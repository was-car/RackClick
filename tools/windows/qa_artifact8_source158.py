"""Closed artifact-only143 ->158 identity, schema8 throughout. No launches."""
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
from qa_schema8_source143 import read_database

SOURCE_MANIFEST = ROOT / 'evidence/s1-20261017/quince-tandas-129-143/CANDIDATA143-FINAL02.json'
SOURCE_SHA256 = '734bc6efd781c385138ab3162d70a08c3ea92b621e6ed9145f58106790ea17c1'
TARGET_MANIFEST = ROOT / 'evidence/s1-20261017/quince-tandas-144-158/CANDIDATA158-FINAL02.json'
TARGET158 = ('evidence/s1-20261017/quince-tandas-144-158/CANDIDATA158-FINAL02.json', '22807251dcf02cb8f86d91064452bdb175840cd77acc361c450a2ac364789baf')
CHANGED_FIELDS = frozenset(('artifactDirectory', 'dllSha256', 'bundleSha256'))


class UpdateError(RuntimeError):
    def __init__(self, code, result=None):
        super().__init__(code)
        self.code, self.result = code, result


def target_pin():
    if (not isinstance(TARGET158, tuple) or len(TARGET158) != 2 or
            TARGET158[0] != TARGET_MANIFEST.relative_to(ROOT).as_posix() or
            not isinstance(TARGET158[1], str) or not re.fullmatch('[0-9a-f]{64}', TARGET158[1])):
        raise UpdateError('target158_pin_pending')
    return TARGET158[1]


def require_same_sql8(candidate, baseline):
    sql = lambda tree: {k: v for k, v in tree['server'].items() if k.startswith('database/')}
    if sql(candidate) != sql(baseline) or len(sql(candidate)) != 8:
        raise UpdateError('schema8_sql_must_be_identical')


def require_config_change(previous, selected):
    missing = object()
    changed = {k for k in previous.keys() | selected.keys() if previous.get(k, missing) != selected.get(k, missing)}
    if not changed or not changed <= CHANGED_FIELDS or 'artifactDirectory' not in changed:
        raise UpdateError('selected_configuration_differs')
    return changed


@dataclass(frozen=True)
class Distribution158:
    revision: int
    manifest: Path
    server: Path
    frontend: Path
    expected: dict

    def validate(self):
        if self.revision == 143:
            manifest, pin = SOURCE_MANIFEST, SOURCE_SHA256
        elif self.revision == 158:
            manifest, pin = TARGET_MANIFEST, target_pin()
        else:
            raise UpdateError('only_closed_transition143_158_supported')
        if self.manifest != manifest or sha256(checked_path(manifest)) != pin:
            raise UpdateError('closed_manifest_not_approved')
        data = json.loads(manifest.read_bytes())
        if (data.get('schema') != 8 or self.server != checked_path(ROOT / Path(data['serverDll']).parent) or
                self.frontend != checked_path(ROOT / data['frontend']) or self.expected != data['distributions'] or
                not self.server.is_relative_to(ROOT / '.local/candidates') or
                not self.frontend.is_relative_to(ROOT / '.local/candidates')):
            raise UpdateError('closed_distribution_identity_changed')
        actual = {'server': artifact_manifest(self.server), 'frontend': artifact_manifest(self.frontend)}
        if actual != self.expected or len(actual['server']) != 17 or len(actual['frontend']) != 18:
            raise UpdateError('complete_closed_distribution_differs')
        sqls = sorted(k for k in actual['server'] if k.startswith('database/'))
        if ([int(Path(n).name[:3]) for n in sqls] != list(range(1, 9)) or
                any(not re.fullmatch(r'database/[0-9]{3}-[a-z0-9-]+\.sql', n) for n in sqls)):
            raise UpdateError('closed_sql_sequence_differs')
        if self.revision == 158:
            baseline = load_source().expected
            require_same_sql8(actual, baseline)
            for name in ('Npgsql.dll', 'RackClick.Server.deps.json', 'RackClick.Server.runtimeconfig.json'):
                if actual['server'].get(name) != baseline['server'].get(name):
                    raise UpdateError('dependency_or_runtime_pin_changed')
            if actual['frontend'].get('app.css') != baseline['frontend'].get('app.css'):
                raise UpdateError('approved_css_changed')
            if actual == baseline:
                raise UpdateError('transition_has_no_artifact_change')
        return actual


def _load(revision, manifest, pin):
    if sha256(checked_path(manifest)) != pin:
        raise UpdateError('closed_manifest_not_approved')
    data = json.loads(manifest.read_bytes())
    distribution = Distribution158(revision, manifest, checked_path(ROOT / Path(data['serverDll']).parent),
                                   checked_path(ROOT / data['frontend']), data['distributions'])
    distribution.validate()
    return distribution


def load_source():
    return _load(143, SOURCE_MANIFEST, SOURCE_SHA256)


def load_target():
    return _load(158, TARGET_MANIFEST, target_pin())


class Source8(Source4):
    """Only inherits READ ONLY SQL/cluster/artifact helpers; never Source7."""
    def __init__(self, directory, pointer, *, real=False):
        try:
            self.directory, self.pointer = checked_path(directory), checked_path(pointer)
            if (self.directory.parent != ROOT / '.local/labs' or
                    not re.fullmatch(r'manual-qa-rc9-schema8-[0-9a-f]{32}', self.directory.name)):
                raise UpdateError('source8_directory_invalid')
            allowed = ROOT / '.local/qa-rc9/current.json' if real else self.directory / 'artifact8-home/current.json'
            if self.pointer != allowed:
                raise UpdateError('explicit_source8_profile_required')
            self.real = real
            self.pointer_bytes = self.pointer.read_bytes()
            if json.loads(self.pointer_bytes) != {'directory': str(self.directory)}:
                raise UpdateError('source8_pointer_differs')
            cfg_path = checked_path(self.directory / 'manual-qa.json')
            self.config_bytes = cfg_path.read_bytes()
            self.cfg = json.loads(self.config_bytes)
            self.meta = json.loads(checked_path(self.directory / 'lab.json').read_bytes())
            c, m = self.cfg, self.meta
            if (c.get('directory') != str(self.directory) or c.get('profile') != 'rc9' or
                    c.get('host') != '127.0.0.1' or m.get('host') != '127.0.0.1' or
                    m.get('path') != str(self.directory) or m.get('postgresql') != '17' or
                    self.directory.name != 'manual-qa-rc9-schema8-' + m.get('id', '!') or
                    c.get('pgPort') != m.get('port') or
                    any(type(c.get(k)) is not int or not 1 <= c[k] <= 65535 for k in ('pgPort', 'webPort')) or
                    c['pgPort'] == c['webPort'] or real and c['webPort'] != 52346):
                raise UpdateError('source8_configuration_invalid')
            rows = [r for r in m['databases'] if r['name'] == c.get('database') and r['label'] == 'manual-qa-rc9']
            if len(rows) != 1:
                raise UpdateError('source8_database_membership_invalid')
            self.db = read_database(self.directory, rows[0], c['pgPort'])
            if c['connection'] != self.db.connection(c['pgPort']):
                raise UpdateError('source8_private_connection_invalid')
            self.baseline = load_source()
            self.art = checked_path(c.get('artifactDirectory', self.directory))
            if self.art != self.directory and self.art.parent != checked_path(self.directory / 'versions'):
                raise UpdateError('source8_artifact_directory_invalid')
            if (c.get('dllSha256') != self.baseline.expected['server']['RackClick.Server.dll'] or
                    c.get('bundleSha256') != self.baseline.expected['frontend']['app.js'] or
                    self.artifacts() != self.baseline.expected):
                raise UpdateError('source8_complete_pair143_differs')
            checked_path(self.directory / 'data')
            self.pg_bin = toolchain()['postgresql'].parent
            self.admin_passfile = checked_path(self.directory / 'admin.pgpass')
            admin = self.admin_passfile.read_text(encoding='utf-8').splitlines()
            if len(admin) != 1 or not admin[0].startswith(f'127.0.0.1:{c["pgPort"]}:*:rc_lab_admin:') or not admin[0].split(':', 4)[-1]:
                raise UpdateError('source8_admin_passfile_invalid')
            self.inputs = [self.directory / 'lab.json', self.db.directory / 'credentials.json',
                           self.db.directory / 'owner.pgpass', self.admin_passfile]
            self.inputs += [self.directory / n for n in PRIVATE_FILES]
            self.hashes = {p.relative_to(self.directory).as_posix(): sha256(checked_path(p)) for p in self.inputs}
            self.original_hashes = {'manual-qa.json': sha256(cfg_path), **self.hashes}
            app_stopped(self.directory, c['webPort'])
        except UpdateError:
            raise
        except Exception:
            raise UpdateError('source8_validation_failed') from None

    def check_schema8(self):
        self.check_cluster_identity()
        if self.sql('SELECT current_database();SELECT current_user;SHOW port') != f'{self.db.name}\n{self.db.owner}\n{self.cfg["pgPort"]}':
            raise UpdateError('source8_running_identity_differs')
        return history(self.sql, self.art / 'server', 8)

    def unchanged(self, expected_config=None, *, quiet=True):
        if {p.relative_to(self.directory).as_posix(): sha256(checked_path(p)) for p in self.inputs} != self.hashes:
            raise UpdateError('source8_immutable_inputs_changed')
        if self.artifacts() != self.baseline.expected or self.pointer.read_bytes() != self.pointer_bytes:
            raise UpdateError('source8_pointer_or_artifacts_changed')
        expected = self.config_bytes if expected_config is None else expected_config
        if checked_path(self.directory / 'manual-qa.json').read_bytes() != expected:
            raise UpdateError('source8_configuration_changed')
        if quiet:
            app_stopped(self.directory, self.cfg['webPort'])
