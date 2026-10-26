"""Closed source712/11 -> target832-02/11 contracts; static/read-only only.

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

SOURCE_MANIFEST = ROOT / 'evidence/s1-20261018/sesenta-tandas-653-712/CANDIDATA712-FINAL02.json'
SOURCE_SHA256 = 'f256c0fc5c99c4ff24c05e36a7eddc0ed2da9d66979db3502e0c4d606ac881cd'
TARGET_MANIFEST = ROOT / 'evidence/s1-20261018/sesenta-tandas-773-832/CANDIDATA832-02.json'
TARGET847 = (TARGET_MANIFEST.relative_to(ROOT).as_posix(), '511c097bafd5baf7590da15287a0dbd53bb5eb8e2fde33931c940b2885e7dfc5')
TABLES11 = frozenset(('schema_migration','systemhaus','customer','app_user','user_group','user_group_member',
    'customer_group','customer_group_member','permission_grant','app_session','operation','audit_event',
    'inventory_site','inventory_building','inventory_room','inventory_rack','inventory_device','inventory_port_group',
    'inventory_port','inventory_connection','inventory_connection_endpoint','operation_cancellation','audit_context',
    'audit_context_object','user_catalog_favorites','user_catalog_favorite','user_catalog_favorite_operation',
    'user_device_templates','user_device_template','user_device_template_operation','customer_device_templates',
    'customer_device_template','customer_device_template_operation','user_preferences','user_preference_operation'))


class Xls11Error(RuntimeError):
    def __init__(self, code, result=None):
        super().__init__(code)
        self.code, self.result = code, result


# Explicit local alias for the historical coordinator's public calling shape.
Schema11Error = Xls11Error


@dataclass(frozen=True)
class Distribution847:
    revision: int
    schema: int
    server: Path
    frontend: Path
    expected: dict
    manifest: Path

    def validate(self):
        if self.revision == 712:
            path, pin = SOURCE_MANIFEST, SOURCE_SHA256
        elif self.revision == 832:
            path, pin = target_pin()
        else:
            raise Xls11Error('only_closed_712_to832_supported')
        if self.schema != 11 or not isinstance(pin, str) or not re.fullmatch('[0-9a-f]{64}', pin):
            raise Xls11Error('closed847_schema_or_pin_invalid')
        if self.manifest != path or sha256(checked_path(path)) != pin:
            raise Xls11Error('closed847_manifest_not_approved')
        value = json.loads(path.read_bytes())
        if (value.get('schema') != 11 or
                self.server != checked_path(ROOT / Path(value['serverDll']).parent) or
                self.frontend != checked_path(ROOT / value['frontend']) or
                self.expected != value['distributions']):
            raise Xls11Error('closed847_distribution_identity_changed')
        if any(not p.is_relative_to(ROOT / '.local/candidates') for p in (self.server, self.frontend)):
            raise Xls11Error('frozen847_candidate_distribution_required')
        actual = {'server': artifact_manifest(self.server), 'frontend': artifact_manifest(self.frontend)}
        total = sum(p.stat().st_size for parent in (self.server, self.frontend) for p in parent.rglob('*') if p.is_file())
        if (actual != self.expected or len(actual['server']) != 20 or len(actual['frontend']) != 18 or
                value.get('fileCount') != 38 or value.get('totalBytes') != total):
            raise Xls11Error('complete847_closed_distribution_differs')
        sqls = sorted(n for n in actual['server'] if n.startswith('database/'))
        if (len(sqls) != 11 or any(not re.fullmatch(r'database/[0-9]{3}-[a-z0-9-]+\.sql', n) for n in sqls) or
                [int(Path(n).name[:3]) for n in sqls] != list(range(1, 12))):
            raise Xls11Error('closed847_sql_sequence_differs')
        if self.revision == 832:
            old = load_source().expected
            if {n: v for n, v in actual['server'].items() if n.startswith('database/')} != {
                    n: v for n, v in old['server'].items() if n.startswith('database/')}:
                raise Xls11Error('closed847_sql001_011_changed')
            for name in ('Npgsql.dll', 'RackClick.Server.deps.json', 'RackClick.Server.runtimeconfig.json'):
                if actual['server'].get(name) != old['server'].get(name):
                    raise Xls11Error('closed847_dependency_or_runtime_pin_changed')
            if actual['frontend'].get('app.css') != old['frontend'].get('app.css'):
                raise Xls11Error('closed847_approved_css_changed')
        return actual


def _load(revision, path, pin):
    if not isinstance(pin, str) or not re.fullmatch('[0-9a-f]{64}', pin) or sha256(checked_path(path)) != pin:
        raise Xls11Error('closed847_manifest_not_approved')
    value = json.loads(path.read_bytes())
    distribution = Distribution847(revision, 11, checked_path(ROOT / Path(value['serverDll']).parent),
        checked_path(ROOT / value['frontend']), value['distributions'], path)
    distribution.validate()
    return distribution


def load_source():
    return _load(712, SOURCE_MANIFEST, SOURCE_SHA256)


def target_pin():
    if (not isinstance(TARGET847, tuple) or len(TARGET847) != 2 or
            TARGET847[0] != TARGET_MANIFEST.relative_to(ROOT).as_posix() or
            not isinstance(TARGET847[1], str) or not re.fullmatch('[0-9a-f]{64}', TARGET847[1])):
        raise Xls11Error('target847_pin_invalid')
    return TARGET_MANIFEST, TARGET847[1]


def load_target():
    path, pin = target_pin()
    return _load(832, path, pin)


class Source712(Source4):
    """Inherits READ ONLY SQL and cluster checks, with a closed pair712 identity."""
    def __init__(self, directory, pointer, *, real=False, selected=None):
        try:
            self.directory, self.pointer = checked_path(directory), checked_path(pointer)
            if (self.directory.parent != ROOT / '.local/labs' or
                    not re.fullmatch(r'manual-qa-rc9-schema11-[0-9a-f]{32}', self.directory.name)):
                raise Xls11Error('source712_directory_invalid')
            allowed = ROOT / '.local/qa-rc9/current.json' if real else self.directory / 'xls11-home/current.json'
            if self.pointer != allowed:
                raise Xls11Error('explicit_source712_profile_required')
            self.real = real
            self.pointer_bytes = self.pointer.read_bytes()
            expected = self.directory if selected is None else checked_candidate_directory(selected)
            if json.loads(self.pointer_bytes) != {'directory': str(expected)}:
                raise Xls11Error('source712_pointer_differs')
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
                raise Xls11Error('source712_configuration_invalid')
            rows = [r for r in m['databases'] if r['name'] == c.get('database') and r['label'] == 'manual-qa-rc9']
            if len(rows) != 1:
                raise Xls11Error('source712_database_membership_invalid')
            self.db = read_database(self.directory, rows[0], c['pgPort'])
            if c['connection'] != self.db.connection(c['pgPort']):
                raise Xls11Error('source712_private_connection_invalid')
            self.baseline = load_source()
            self.art = checked_path(c.get('artifactDirectory', self.directory))
            if self.art != self.directory and self.art.parent != checked_path(self.directory / 'versions'):
                raise Xls11Error('source712_artifact_directory_invalid')
            if (c.get('dllSha256') != self.baseline.expected['server']['RackClick.Server.dll'] or
                    c.get('bundleSha256') != self.baseline.expected['frontend']['app.js'] or
                    self.artifacts() != self.baseline.expected):
                raise Xls11Error('source712_complete_pair_differs')
            checked_path(self.directory / 'data')
            self.pg_bin = toolchain()['postgresql'].parent
            self.admin_passfile = checked_path(self.directory / 'admin.pgpass')
            admin = self.admin_passfile.read_text(encoding='utf-8').splitlines()
            if len(admin) != 1 or not admin[0].startswith(f'127.0.0.1:{c["pgPort"]}:*:rc_lab_admin:') or not admin[0].split(':', 4)[-1]:
                raise Xls11Error('source712_admin_passfile_invalid')
            databases = m['databases']
            if (not isinstance(databases, list) or not databases or
                    len({r['name'] for r in databases}) != len(databases) or
                    len({r['label'] for r in databases}) != len(databases)):
                raise Xls11Error('source712_complete_database_membership_invalid')
            self.databases = [read_database(self.directory, row, c['pgPort']) for row in databases]
            self.postgresql_secrets = {admin[0].split(':', 4)[-1]}
            self.inputs = [cfg_path, self.directory / 'lab.json', self.admin_passfile]
            for database in self.databases:
                self.inputs += [database.directory / 'credentials.json', database.directory / 'owner.pgpass']
                self.postgresql_secrets.update((database.owner_password, database.runtime_password))
            init_password = checked_path(self.directory / 'init-password.txt')
            if init_password.exists():
                if init_password.read_text(encoding='utf-8') != admin[0].split(':', 4)[-1] + '\n':
                    raise Xls11Error('source712_init_password_differs')
                self.inputs.append(init_password)
            self.inputs += [self.directory / n for n in PRIVATE_FILES]
            self.hashes = {p.relative_to(self.directory).as_posix(): sha256(checked_path(p)) for p in self.inputs}
            app_stopped(self.directory, c['webPort'])
        except Xls11Error:
            raise
        except Exception:
            raise Xls11Error('source712_validation_failed') from None

    def check_schema11(self):
        self.check_cluster_identity()
        if self.sql('SELECT current_database();SELECT current_user;SHOW port') != f'{self.db.name}\n{self.db.owner}\n{self.cfg["pgPort"]}':
            raise Xls11Error('source712_running_identity_differs')
        return history(self.sql, self.art / 'server', 11)

    def unchanged(self, *, pointer=True, quiet=True):
        if {p.relative_to(self.directory).as_posix(): sha256(checked_path(p)) for p in self.inputs} != self.hashes:
            raise Xls11Error('source712_immutable_inputs_changed')
        if self.artifacts() != self.baseline.expected:
            raise Xls11Error('source712_artifacts_changed')
        if pointer and self.pointer.read_bytes() != self.pointer_bytes:
            raise Xls11Error('source712_pointer_changed')
        if quiet:
            app_stopped(self.directory, self.cfg['webPort'])


def checked_candidate_directory(directory):
    directory = checked_path(directory)
    if (directory.parent != ROOT / '.local/labs' or
            not re.fullmatch(r'manual-qa-rc9-schema11-[0-9a-f]{32}', directory.name)):
        raise Xls11Error('candidate847_directory_invalid')
    return directory
