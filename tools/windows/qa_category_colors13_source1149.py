"""Closed source969/12 -> target1089/13 contracts; static/read-only only.

A schema alone does not identify a distribution: revision and pinned complete pair do.
No CLI override, migration, implicit build or current-QA discovery is supported.
"""
from dataclasses import dataclass
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'development/server/tests'))
from pg_support import toolchain
from pg_lab_recovery import sha256
from qa_schema5_candidate import checked_path
from qa_schema6_source import Source4, PRIVATE_FILES, artifact_manifest, app_stopped
from qa_schema6_real_candidate import history
from qa_schema11_source772 import read_database
from qa_schema_switch import read_owner
from qa_schema_candidate import snapshot
from qa_port_colors12_candidate1029 import load_prepared as load_prepared1029, PREPARED as PREPARED1029, SEAL as SEAL1029
from qa_port_colors12_source1029 import TABLES11, NEW_TABLES as PORT_TABLES12

SOURCE_MANIFEST = ROOT / 'evidence/s1-20261018/sesenta-tandas-970-1029/CANDIDATA969-FIX02.json'
SOURCE_SHA256 = 'b589609154fed1567106ef0865972155258f0f5474128c73076f4697d43b8bda'
TARGET_MANIFEST = ROOT / 'evidence/s1-20261018/sesenta-tandas-1030-1089/CANDIDATA1089-02.json'
TARGET1149 = (TARGET_MANIFEST.relative_to(ROOT).as_posix(), 'c8b3df5b8e0fb6c5db148b7ddca2a8064ade6b90557713fb0835cbf69bb9710c')
NEW_TABLES = frozenset(('user_category_colors', 'user_category_color_operation'))
TABLES12 = TABLES11 | PORT_TABLES12


class CategoryColors13Error(RuntimeError):
    def __init__(self, code, result=None):
        super().__init__(code)
        self.code, self.result = code, result


# Explicit local alias for the historical coordinator's public calling shape.
Schema13Error = CategoryColors13Error


@dataclass(frozen=True)
class Distribution1149:
    revision: int
    schema: int
    server: Path
    frontend: Path
    expected: dict
    manifest: Path

    def validate(self):
        if self.revision == 969:
            path, pin = SOURCE_MANIFEST, SOURCE_SHA256
        elif self.revision == 1089:
            path, pin = target_pin()
        else:
            raise CategoryColors13Error('only_closed_969_to1089_supported')
        if self.schema != (12 if self.revision == 969 else 13) or not isinstance(pin, str) or not re.fullmatch('[0-9a-f]{64}', pin):
            raise CategoryColors13Error('closed1149_schema_or_pin_invalid')
        if self.manifest != path or sha256(checked_path(path)) != pin:
            raise CategoryColors13Error('closed1149_manifest_not_approved')
        value = json.loads(path.read_bytes())
        if (value.get('schema') != self.schema or
                self.server != checked_path(ROOT / Path(value['serverDll']).parent) or
                self.frontend != checked_path(ROOT / value['frontend']) or
                self.expected != value['distributions']):
            raise CategoryColors13Error('closed1149_distribution_identity_changed')
        if any(not p.is_relative_to(ROOT / '.local/candidates') for p in (self.server, self.frontend)):
            raise CategoryColors13Error('frozen1149_candidate_distribution_required')
        actual = {'server': artifact_manifest(self.server), 'frontend': artifact_manifest(self.frontend)}
        total = sum(p.stat().st_size for parent in (self.server, self.frontend) for p in parent.rglob('*') if p.is_file())
        if (actual != self.expected or len(actual['server']) != self.schema + 9 or len(actual['frontend']) != 18 or
                value.get('fileCount') != self.schema + 27 or value.get('totalBytes') != total or
                total != (7037914 if self.schema == 12 else 7133395)):
            raise CategoryColors13Error('complete1149_closed_distribution_differs')
        sqls = sorted(n for n in actual['server'] if n.startswith('database/'))
        if (len(sqls) != self.schema or any(not re.fullmatch(r'database/[0-9]{3}-[a-z0-9-]+\.sql', n) for n in sqls) or
                [int(Path(n).name[:3]) for n in sqls] != list(range(1, self.schema + 1))):
            raise CategoryColors13Error('closed1149_sql_sequence_differs')
        if self.revision == 1089:
            old = load_source().expected
            if any(actual['server'].get(k) != v for k,v in old['server'].items() if k.startswith('database/')):
                raise CategoryColors13Error('closed1149_historical_sql001_012_changed')
            for name in ('Npgsql.dll', 'RackClick.Server.deps.json', 'RackClick.Server.runtimeconfig.json'):
                if actual['server'].get(name) != old['server'].get(name):
                    raise CategoryColors13Error('closed1149_dependency_or_runtime_changed')
            if ({k:v for k,v in actual['frontend'].items() if k != 'app.js'} !=
                    {k:v for k,v in old['frontend'].items() if k != 'app.js'} or
                    actual['frontend']['app.js'] == old['frontend']['app.js']):
                raise CategoryColors13Error('closed1149_only_reviewed_bundle_change_allowed')
        return actual


def _load(revision, path, pin):
    if not isinstance(pin, str) or not re.fullmatch('[0-9a-f]{64}', pin) or sha256(checked_path(path)) != pin:
        raise CategoryColors13Error('closed1149_manifest_not_approved')
    value = json.loads(path.read_bytes())
    distribution = Distribution1149(revision, 12 if revision == 969 else 13, checked_path(ROOT / Path(value['serverDll']).parent),
        checked_path(ROOT / value['frontend']), value['distributions'], path)
    distribution.validate()
    return distribution


def load_source():
    return _load(969, SOURCE_MANIFEST, SOURCE_SHA256)


def target_pin():
    if (not isinstance(TARGET1149, tuple) or len(TARGET1149) != 2 or
            TARGET1149[0] != TARGET_MANIFEST.relative_to(ROOT).as_posix() or
            not isinstance(TARGET1149[1], str) or not re.fullmatch('[0-9a-f]{64}', TARGET1149[1])):
        raise CategoryColors13Error('target1149_pin_invalid')
    return TARGET_MANIFEST, TARGET1149[1]


def load_target():
    path, pin = target_pin()
    return _load(1089, path, pin)


class Source969(Source4):
    """Inherits READ ONLY SQL and cluster checks, with a closed pair969 identity."""
    def __init__(self, directory, pointer, *, real=False, selected=None):
        try:
            self.directory, self.pointer = checked_path(directory), checked_path(pointer)
            if (self.directory.parent != ROOT / '.local/labs' or
                    not re.fullmatch(r'manual-qa-rc9-schema12-[0-9a-f]{32}', self.directory.name)):
                raise CategoryColors13Error('source969_directory_invalid')
            allowed = ROOT / '.local/qa-rc9/current.json' if real else self.directory / 'category-colors13-home/current.json'
            if self.pointer != allowed:
                raise CategoryColors13Error('explicit_source969_profile_required')
            self.real = real
            self.pointer_bytes = self.pointer.read_bytes()
            expected = self.directory if selected is None else checked_candidate_directory(selected)
            if json.loads(self.pointer_bytes) != {'directory': str(expected)}:
                raise CategoryColors13Error('source969_pointer_differs')
            cfg_path = checked_path(self.directory / 'manual-qa.json')
            self.config_bytes = cfg_path.read_bytes()
            self.cfg = json.loads(self.config_bytes)
            self.meta = json.loads(checked_path(self.directory / 'lab.json').read_bytes())
            c, m = self.cfg, self.meta
            if (c.get('directory') != str(self.directory) or c.get('profile') != 'rc9' or
                    c.get('host') != '127.0.0.1' or m.get('host') != '127.0.0.1' or
                    m.get('path') != str(self.directory) or m.get('postgresql') != '17' or
                    self.directory.name != 'manual-qa-rc9-schema12-' + m.get('id', '!') or
                    c.get('pgPort') != m.get('port') or
                    any(type(c.get(k)) is not int or not 1 <= c[k] <= 65535 for k in ('pgPort', 'webPort')) or
                    c['pgPort'] == c['webPort'] or real and c['webPort'] != 52346):
                raise CategoryColors13Error('source969_configuration_invalid')
            rows = [r for r in m['databases'] if r['name'] == c.get('database') and r['label'] == 'manual-qa-rc9']
            if len(rows) != 1:
                raise CategoryColors13Error('source969_database_membership_invalid')
            self.db = read_database(self.directory, rows[0], c['pgPort'])
            if c['connection'] != self.db.connection(c['pgPort']):
                raise CategoryColors13Error('source969_private_connection_invalid')
            self.baseline = load_source()
            self.art = checked_path(c.get('artifactDirectory', self.directory))
            if self.art != self.directory and self.art.parent != checked_path(self.directory / 'versions'):
                raise CategoryColors13Error('source969_artifact_directory_invalid')
            if (c.get('dllSha256') != self.baseline.expected['server']['RackClick.Server.dll'] or
                    c.get('bundleSha256') != self.baseline.expected['frontend']['app.js'] or
                    self.artifacts() != self.baseline.expected):
                raise CategoryColors13Error('source969_complete_pair_differs')
            checked_path(self.directory / 'data')
            self.pg_bin = toolchain()['postgresql'].parent
            self.admin_passfile = checked_path(self.directory / 'admin.pgpass')
            admin = self.admin_passfile.read_text(encoding='utf-8').splitlines()
            if len(admin) != 1 or not admin[0].startswith(f'127.0.0.1:{c["pgPort"]}:*:rc_lab_admin:') or not admin[0].split(':', 4)[-1]:
                raise CategoryColors13Error('source969_admin_passfile_invalid')
            databases = m['databases']
            if (not isinstance(databases, list) or not databases or
                    len({r['name'] for r in databases}) != len(databases) or
                    len({r['label'] for r in databases}) != len(databases)):
                raise CategoryColors13Error('source969_complete_database_membership_invalid')
            self.databases = [read_database(self.directory, row, c['pgPort']) for row in databases]
            self.postgresql_secrets = {admin[0].split(':', 4)[-1]}
            self.inputs = [cfg_path, self.directory / 'lab.json', self.admin_passfile]
            for database in self.databases:
                self.inputs += [database.directory / 'credentials.json', database.directory / 'owner.pgpass']
                self.postgresql_secrets.update((database.owner_password, database.runtime_password))
            init_password = checked_path(self.directory / 'init-password.txt')
            if init_password.exists():
                if init_password.read_text(encoding='utf-8') != admin[0].split(':', 4)[-1] + '\n':
                    raise CategoryColors13Error('source969_init_password_differs')
                self.inputs.append(init_password)
            self.inputs += [self.directory / n for n in PRIVATE_FILES]
            self.inputs += [self.directory / 'data' / n for n in ('postgresql.conf','pg_hba.conf','pg_ident.conf')]
            # Source969 is the complete branch prepared by1029. Its recovery849
            # files/seals remain evidence; live DB rows may legitimately differ
            # from that old preparation and from the primary after user QA.
            self.prepared1029 = load_prepared1029(self.directory)
            if (self.prepared1029.cfg != self.cfg or len(self.databases) != 2 or
                    self.prepared1029.database.name != self.db.name or
                    self.prepared1029.recovered.name not in {d.name for d in self.databases}):
                raise CategoryColors13Error('source969_prepared1029_binding_differs')
            self.recovery_cfg = self.prepared1029.recovery_cfg
            self.recovery_art = checked_path(self.directory / 'versions/port-colors12-source849-recovery')
            self.inputs += [self.directory / PREPARED1029, self.directory / SEAL1029]
            self.inputs += [self.directory / n for n in self.prepared1029.record['inputHashes']]
            self.inputs = sorted({checked_path(p) for p in self.inputs})
            self.hashes = {p.relative_to(self.directory).as_posix(): sha256(checked_path(p)) for p in self.inputs}
            app_stopped(self.directory, c['webPort'])
        except CategoryColors13Error:
            raise
        except Exception:
            raise CategoryColors13Error('source969_validation_failed') from None

    def check_schema12(self):
        self.check_cluster_identity()
        if self.sql('SELECT current_database();SELECT current_user;SHOW port') != f'{self.db.name}\n{self.db.owner}\n{self.cfg["pgPort"]}':
            raise CategoryColors13Error('source969_running_identity_differs')
        return history(self.sql, self.art / 'server', 12)

    def unchanged(self, *, pointer=True, quiet=True):
        if {p.relative_to(self.directory).as_posix(): sha256(checked_path(p)) for p in self.inputs} != self.hashes:
            raise CategoryColors13Error('source969_immutable_inputs_changed')
        if self.artifacts() != self.baseline.expected:
            raise CategoryColors13Error('source969_artifacts_changed')
        self.prepared1029.validate_static()
        if pointer and self.pointer.read_bytes() != self.pointer_bytes:
            raise CategoryColors13Error('source969_pointer_changed')
        if quiet:
            app_stopped(self.directory, self.cfg['webPort'])

    def database_states(self, *, primary_snapshot=None, primary_history=None):
        """Current states of both source DBs, independently; strictly READ ONLY."""
        self.check_cluster_identity()
        recovery = lambda q: read_owner(self.directory, self.recovery_cfg, q)
        secondary = self.prepared1029.recovered
        if recovery('SELECT current_database();SELECT current_user;SHOW port') != f'{secondary.name}\n{secondary.owner}\n{self.cfg["pgPort"]}':
            raise CategoryColors13Error('source969_recovery849_running_identity_differs')
        primary_snapshot = snapshot(self.sql) if primary_snapshot is None else primary_snapshot
        primary_history = self.check_schema12() if primary_history is None else primary_history
        secondary_snapshot = snapshot(recovery)
        if set(primary_snapshot) != TABLES12 or set(secondary_snapshot) != TABLES11:
            raise CategoryColors13Error('source969_complete_database_table_sets_differ')
        return {
            'primary':dict(database=self.db.name, revision=969, schema=12,
                           snapshot=primary_snapshot, history=primary_history),
            'recovery849':dict(database=secondary.name, revision=849, schema=11,
                               snapshot=secondary_snapshot, history=history(recovery,self.recovery_art / 'server',11))}


def checked_candidate_directory(directory):
    directory = checked_path(directory)
    if (directory.parent != ROOT / '.local/labs' or
            not re.fullmatch(r'manual-qa-rc9-schema13-[0-9a-f]{32}', directory.name)):
        raise CategoryColors13Error('candidate1149_directory_invalid')
    return directory
