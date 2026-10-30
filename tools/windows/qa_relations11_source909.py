"""Closed source832/11 -> target849/11 contracts; static/read-only only.

Schema11 does not identify a distribution: revision and pinned complete pair do.
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
from qa_xls11_candidate847 import load_prepared as load_prepared847, PREPARED as PREPARED847, SEAL as SEAL847

SOURCE_MANIFEST = ROOT / 'evidence/s1-20261018/sesenta-tandas-773-832/CANDIDATA832-02.json'
SOURCE_SHA256 = '511c097bafd5baf7590da15287a0dbd53bb5eb8e2fde33931c940b2885e7dfc5'
TARGET_MANIFEST = ROOT / 'evidence/s1-20261018/tanda-849/CANDIDATA849.json'
TARGET909 = (TARGET_MANIFEST.relative_to(ROOT).as_posix(), '1b40f9ceffde0503c024f0dce1fb79de02c05a21bc9cb93ad3b0d6a3d359dc09')
TABLES11 = frozenset(('schema_migration','systemhaus','customer','app_user','user_group','user_group_member',
    'customer_group','customer_group_member','permission_grant','app_session','operation','audit_event',
    'inventory_site','inventory_building','inventory_room','inventory_rack','inventory_device','inventory_port_group',
    'inventory_port','inventory_connection','inventory_connection_endpoint','operation_cancellation','audit_context',
    'audit_context_object','user_catalog_favorites','user_catalog_favorite','user_catalog_favorite_operation',
    'user_device_templates','user_device_template','user_device_template_operation','customer_device_templates',
    'customer_device_template','customer_device_template_operation','user_preferences','user_preference_operation'))


class Relations11Error(RuntimeError):
    def __init__(self, code, result=None):
        super().__init__(code)
        self.code, self.result = code, result


# Explicit local alias for the historical coordinator's public calling shape.
Schema11Error = Relations11Error


@dataclass(frozen=True)
class Distribution909:
    revision: int
    schema: int
    server: Path
    frontend: Path
    expected: dict
    manifest: Path

    def validate(self):
        if self.revision == 832:
            path, pin = SOURCE_MANIFEST, SOURCE_SHA256
        elif self.revision == 849:
            path, pin = target_pin()
        else:
            raise Relations11Error('only_closed_832_to849_supported')
        if self.schema != 11 or not isinstance(pin, str) or not re.fullmatch('[0-9a-f]{64}', pin):
            raise Relations11Error('closed909_schema_or_pin_invalid')
        if self.manifest != path or sha256(checked_path(path)) != pin:
            raise Relations11Error('closed909_manifest_not_approved')
        value = json.loads(path.read_bytes())
        if (value.get('schema') != 11 or
                self.server != checked_path(ROOT / Path(value['serverDll']).parent) or
                self.frontend != checked_path(ROOT / value['frontend']) or
                self.expected != value['distributions']):
            raise Relations11Error('closed909_distribution_identity_changed')
        if any(not p.is_relative_to(ROOT / '.local/candidates') for p in (self.server, self.frontend)):
            raise Relations11Error('frozen909_candidate_distribution_required')
        actual = {'server': artifact_manifest(self.server), 'frontend': artifact_manifest(self.frontend)}
        total = sum(p.stat().st_size for parent in (self.server, self.frontend) for p in parent.rglob('*') if p.is_file())
        if (actual != self.expected or len(actual['server']) != 20 or len(actual['frontend']) != 18 or
                value.get('fileCount') != 38 or value.get('totalBytes') != total):
            raise Relations11Error('complete909_closed_distribution_differs')
        sqls = sorted(n for n in actual['server'] if n.startswith('database/'))
        if (len(sqls) != 11 or any(not re.fullmatch(r'database/[0-9]{3}-[a-z0-9-]+\.sql', n) for n in sqls) or
                [int(Path(n).name[:3]) for n in sqls] != list(range(1, 12))):
            raise Relations11Error('closed909_sql_sequence_differs')
        if self.revision == 849:
            old = load_source().expected
            if actual['server'] != old['server']:
                raise Relations11Error('closed909_server_sql_dependencies_changed')
            if ({k:v for k,v in actual['frontend'].items() if k != 'app.js'} !=
                    {k:v for k,v in old['frontend'].items() if k != 'app.js'} or
                    actual['frontend']['app.js'] == old['frontend']['app.js'] or total != 7108622):
                raise Relations11Error('closed909_only_reviewed_bundle_change_allowed')
        return actual


def _load(revision, path, pin):
    if not isinstance(pin, str) or not re.fullmatch('[0-9a-f]{64}', pin) or sha256(checked_path(path)) != pin:
        raise Relations11Error('closed909_manifest_not_approved')
    value = json.loads(path.read_bytes())
    distribution = Distribution909(revision, 11, checked_path(ROOT / Path(value['serverDll']).parent),
        checked_path(ROOT / value['frontend']), value['distributions'], path)
    distribution.validate()
    return distribution


def load_source():
    return _load(832, SOURCE_MANIFEST, SOURCE_SHA256)


def target_pin():
    if (not isinstance(TARGET909, tuple) or len(TARGET909) != 2 or
            TARGET909[0] != TARGET_MANIFEST.relative_to(ROOT).as_posix() or
            not isinstance(TARGET909[1], str) or not re.fullmatch('[0-9a-f]{64}', TARGET909[1])):
        raise Relations11Error('target909_pin_invalid')
    return TARGET_MANIFEST, TARGET909[1]


def load_target():
    path, pin = target_pin()
    return _load(849, path, pin)


class Source832(Source4):
    """Inherits READ ONLY SQL and cluster checks, with a closed pair832 identity."""
    def __init__(self, directory, pointer, *, real=False, selected=None):
        try:
            self.directory, self.pointer = checked_path(directory), checked_path(pointer)
            if (self.directory.parent != ROOT / '.local/labs' or
                    not re.fullmatch(r'manual-qa-rc9-schema11-[0-9a-f]{32}', self.directory.name)):
                raise Relations11Error('source832_directory_invalid')
            allowed = ROOT / '.local/qa-rc9/current.json' if real else self.directory / 'relations11-home/current.json'
            if self.pointer != allowed:
                raise Relations11Error('explicit_source832_profile_required')
            self.real = real
            self.pointer_bytes = self.pointer.read_bytes()
            expected = self.directory if selected is None else checked_candidate_directory(selected)
            if json.loads(self.pointer_bytes) != {'directory': str(expected)}:
                raise Relations11Error('source832_pointer_differs')
            cfg_path = checked_path(self.directory / 'manual-qa.json')
            self.config_bytes = cfg_path.read_bytes()
            self.cfg = json.loads(self.config_bytes)
            self.meta = json.loads(checked_path(self.directory / 'lab.json').read_bytes())
            c, m = self.cfg, self.meta
            if (c.get('directory') != str(self.directory) or c.get('profile') != 'rc9' or
                    c.get('host') != '127.0.0.1' or m.get('host') != '127.0.0.1' or
                    m.get('path') != str(self.directory) or m.get('postgresql') != '17' or
                    self.directory.name != 'manual-qa-rc9-schema11-' + m.get('id', '!') or
                    c.get('pgPort') != m.get('port') or
                    any(type(c.get(k)) is not int or not 1 <= c[k] <= 65535 for k in ('pgPort', 'webPort')) or
                    c['pgPort'] == c['webPort'] or real and c['webPort'] != 52346):
                raise Relations11Error('source832_configuration_invalid')
            rows = [r for r in m['databases'] if r['name'] == c.get('database') and r['label'] == 'manual-qa-rc9']
            if len(rows) != 1:
                raise Relations11Error('source832_database_membership_invalid')
            self.db = read_database(self.directory, rows[0], c['pgPort'])
            if c['connection'] != self.db.connection(c['pgPort']):
                raise Relations11Error('source832_private_connection_invalid')
            self.baseline = load_source()
            self.art = checked_path(c.get('artifactDirectory', self.directory))
            if self.art != self.directory and self.art.parent != checked_path(self.directory / 'versions'):
                raise Relations11Error('source832_artifact_directory_invalid')
            if (c.get('dllSha256') != self.baseline.expected['server']['RackClick.Server.dll'] or
                    c.get('bundleSha256') != self.baseline.expected['frontend']['app.js'] or
                    self.artifacts() != self.baseline.expected):
                raise Relations11Error('source832_complete_pair_differs')
            checked_path(self.directory / 'data')
            self.pg_bin = toolchain()['postgresql'].parent
            self.admin_passfile = checked_path(self.directory / 'admin.pgpass')
            admin = self.admin_passfile.read_text(encoding='utf-8').splitlines()
            if len(admin) != 1 or not admin[0].startswith(f'127.0.0.1:{c["pgPort"]}:*:rc_lab_admin:') or not admin[0].split(':', 4)[-1]:
                raise Relations11Error('source832_admin_passfile_invalid')
            databases = m['databases']
            if (not isinstance(databases, list) or not databases or
                    len({r['name'] for r in databases}) != len(databases) or
                    len({r['label'] for r in databases}) != len(databases)):
                raise Relations11Error('source832_complete_database_membership_invalid')
            self.databases = [read_database(self.directory, row, c['pgPort']) for row in databases]
            self.postgresql_secrets = {admin[0].split(':', 4)[-1]}
            self.inputs = [cfg_path, self.directory / 'lab.json', self.admin_passfile]
            for database in self.databases:
                self.inputs += [database.directory / 'credentials.json', database.directory / 'owner.pgpass']
                self.postgresql_secrets.update((database.owner_password, database.runtime_password))
            init_password = checked_path(self.directory / 'init-password.txt')
            if init_password.exists():
                if init_password.read_text(encoding='utf-8') != admin[0].split(':', 4)[-1] + '\n':
                    raise Relations11Error('source832_init_password_differs')
                self.inputs.append(init_password)
            self.inputs += [self.directory / n for n in PRIVATE_FILES]
            # Source832 is the complete branch prepared by847. Its recovery712
            # files/seals remain evidence; live DB rows may legitimately differ
            # from that old preparation and from the primary after user QA.
            self.prepared847 = load_prepared847(self.directory)
            if (self.prepared847.cfg != self.cfg or len(self.databases) != 2 or
                    self.prepared847.database.name != self.db.name or
                    self.prepared847.recovered.name not in {d.name for d in self.databases}):
                raise Relations11Error('source832_prepared847_binding_differs')
            self.recovery_cfg = self.prepared847.recovery_cfg
            self.recovery_art = checked_path(self.directory / 'versions/xls11-source712-recovery')
            self.inputs += [self.directory / PREPARED847, self.directory / SEAL847]
            self.inputs += [self.directory / n for n in self.prepared847.record['inputHashes']]
            self.inputs = sorted({checked_path(p) for p in self.inputs})
            self.hashes = {p.relative_to(self.directory).as_posix(): sha256(checked_path(p)) for p in self.inputs}
            app_stopped(self.directory, c['webPort'])
        except Relations11Error:
            raise
        except Exception:
            raise Relations11Error('source832_validation_failed') from None

    def check_schema11(self):
        self.check_cluster_identity()
        if self.sql('SELECT current_database();SELECT current_user;SHOW port') != f'{self.db.name}\n{self.db.owner}\n{self.cfg["pgPort"]}':
            raise Relations11Error('source832_running_identity_differs')
        return history(self.sql, self.art / 'server', 11)

    def unchanged(self, *, pointer=True, quiet=True):
        if {p.relative_to(self.directory).as_posix(): sha256(checked_path(p)) for p in self.inputs} != self.hashes:
            raise Relations11Error('source832_immutable_inputs_changed')
        if self.artifacts() != self.baseline.expected:
            raise Relations11Error('source832_artifacts_changed')
        self.prepared847.validate_static()
        if pointer and self.pointer.read_bytes() != self.pointer_bytes:
            raise Relations11Error('source832_pointer_changed')
        if quiet:
            app_stopped(self.directory, self.cfg['webPort'])

    def database_states(self, *, primary_snapshot=None, primary_history=None):
        """Current states of both source DBs, independently; strictly READ ONLY."""
        self.check_cluster_identity()
        recovery = lambda q: read_owner(self.directory, self.recovery_cfg, q)
        secondary = self.prepared847.recovered
        if recovery('SELECT current_database();SELECT current_user;SHOW port') != f'{secondary.name}\n{secondary.owner}\n{self.cfg["pgPort"]}':
            raise Relations11Error('source832_recovery712_running_identity_differs')
        primary_snapshot = snapshot(self.sql) if primary_snapshot is None else primary_snapshot
        primary_history = self.check_schema11() if primary_history is None else primary_history
        secondary_snapshot = snapshot(recovery)
        if set(primary_snapshot) != TABLES11 or set(secondary_snapshot) != TABLES11:
            raise Relations11Error('source832_complete_database_table_sets_differ')
        return {
            'primary':dict(database=self.db.name, revision=832, schema=11,
                           snapshot=primary_snapshot, history=primary_history),
            'recovery712':dict(database=secondary.name, revision=712, schema=11,
                               snapshot=secondary_snapshot, history=history(recovery,self.recovery_art / 'server',11))}


def checked_candidate_directory(directory):
    directory = checked_path(directory)
    if (directory.parent != ROOT / '.local/labs' or
            not re.fullmatch(r'manual-qa-rc9-schema11-[0-9a-f]{32}', directory.name)):
        raise Relations11Error('candidate909_directory_invalid')
    return directory
