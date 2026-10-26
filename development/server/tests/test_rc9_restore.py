"""Three bounded Windows/PostgreSQL tests for the authorized private RC9 backup.

Logs deliberately contain no source identifiers, names or payloads. Each case
uses a fresh database; the manual QA laboratory is never selected or modified.
"""
from __future__ import annotations
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import secrets
import sys
import unittest
import uuid

from pg_support import Client, DEFAULT_DLL, Lab, WORKSPACE
from test_postgres import EvidenceResult, Tee

spec = importlib.util.spec_from_file_location('rc9_restore', WORKSPACE / 'tools/windows/rc9_restore.py')
restore_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(restore_module)
SOURCE = WORKSPACE / 'RackClick-backup-all.json'


class RestorePostgres(unittest.TestCase):
    lab = None

    def setUp(self):
        self.db = self.lab.create_database(self._testMethodName)
        self.password = secrets.token_urlsafe(32)
        result = self.lab.bootstrap(self.db, 'restore-test-admin', self.password)
        self.assertEqual(result.returncode, 0, 'Private bootstrap failed')
        self.actor = self.lab.sql(self.db, 'SELECT id FROM app_user')
        self.lab.grant_runtime(self.db)

    def check(self, condition, message):
        # Never let unittest include potentially private object diffs.
        self.assertTrue(condition, message)

    def error(self, callable_, code):
        try:
            callable_()
        except restore_module.RestoreError as error:
            self.assertEqual(error.code, code)
        else:
            self.fail('Expected explicit restore rejection')

    def test_real_backup_identity_equivalence_and_second_session(self):
        plan = restore_module.analyze(SOURCE)
        report = restore_module.restore(self.lab, self.db, SOURCE, self.actor)
        self.check(report['committed'], 'Restore must commit')
        self.assertEqual(report['counts'], {'customers': 10, 'sites': 15, 'buildings': 25, 'rooms': 68,
            'racks': 68, 'devices': 311, 'portGroups': 633, 'ports': 5408, 'connections': 623,
            'localConnections': 565, 'crossConnections': 58})
        mapping = json.loads(Path(report['mappingPath']).read_text(encoding='utf-8'))
        self.check(mapping['entities'] == plan['mapping']['entities'], 'Private identity map differs')
        self.check((Path(report['mappingPath']).parent / 'original.json').read_bytes() == SOURCE.read_bytes(),
                   'Private original archive must preserve exact bytes')
        # Every persisted column/extension is compared by stable ID; this is not
        # merely a count check. Assertions hide complete source values on failure.
        for table, rows in plan['rows'].items():
            columns = list(rows[0]) if rows else []
            if not rows:
                continue
            projection = ','.join("'" + key + "'," + key for key in columns)
            actual = json.loads(self.lab.sql(self.db,
                f"SELECT jsonb_agg(jsonb_build_object({projection}))::text FROM {table}", sensitive=True))
            key = (lambda row: (row['connection_id'], row['ordinal'])) if table.endswith('_endpoint') else (lambda row: row['id'])
            self.check({key(row): row for row in actual} == {key(row): row for row in rows},
                       'Persisted rows/attributes differ for table ' + table)
        self.assertEqual(self.lab.sql(self.db, "SELECT count(*) FROM audit_event WHERE action='laboratory.rc9.restore'"), '1')
        self.assertEqual(self.lab.sql(self.db, "SELECT has_schema_privilege(" + restore_module.sql_value(self.db.runtime) + ", 'laboratory_restore', 'USAGE')"), 'f')
        self.assertEqual(self.lab.sql(self.db, "SELECT has_table_privilege(" + restore_module.sql_value(self.db.runtime) + ", 'laboratory_restore.rc9_provenance', 'SELECT')"), 'f')
        server = self.lab.start_server(self.db)
        first, second = Client(server), Client(server)
        for client in (first, second):
            self.assertEqual(client.login('restore-test-admin', self.password).status, 200)
            client.actor_id = self.actor
        self.check(first.cookie != second.cookie, 'Two clients must have separate authenticated sessions')
        counters = {key: 0 for key in ['sites', 'buildings', 'rooms', 'racks', 'devices', 'portGroups', 'ports', 'connections']}
        port_rows = {row['id']: row for row in plan['rows']['inventory_port']}
        con_rows = {row['id']: row for row in plan['rows']['inventory_connection']}
        for customer in mapping['entities']['customers']:
            response = second.request('GET', f"/api/v1/customers/{customer['id']}/project")
            self.assertEqual(response.status, 200)
            snapshot = response.json()
            for key in counters:
                counters[key] += len(snapshot[key])
            for port in snapshot['ports']:
                source = port_rows[port['id']]
                self.check(all(port[api] == source[sql] for api, sql in [('deviceId', 'device_id'), ('groupId', 'group_id'),
                    ('type', 'type'), ('gn', 'gn'), ('sortOrder', 'sort_order'), ('label', 'label'), ('status', 'status'),
                    ('poe', 'poe'), ('watts', 'watts'), ('color', 'color'), ('face', 'face'), ('powerRole', 'power_role'),
                    ('properties', 'properties')]), 'API port fields differ from source-mapped storage')
            for connection in snapshot['connections']:
                source = con_rows[connection['id']]
                self.check(all(connection[k] == source[k] for k in ['note', 'color', 'patch', 'properties']),
                           'API cable attributes differ from source-mapped storage')
        self.check(counters == {key: report['counts'][key] for key in counters}, 'API collections omitted source inventory')
        customer_id = mapping['entities']['customers'][0]['id']
        route = f'/api/v1/customers/{customer_id}/project'
        original = first.request('GET', route).json()
        rack_id = original['racks'][0]['id']
        response = first.request('POST', f'/api/v1/customers/{customer_id}/commands',
            {'type': 'rack.update', 'payload': {'id': rack_id, 'name': 'QA restore committed edit'}},
            {'If-Match': f'"{original["revision"]}"', 'Idempotency-Key': str(uuid.uuid4()), 'X-RackClick-Actor': self.actor})
        self.assertEqual(response.status, 200)
        reloaded = second.request('GET', route).json()
        self.check(any(row['id'] == rack_id and row['name'] == 'QA restore committed edit' for row in reloaded['racks']),
                   'Committed edit must be visible from another authenticated session')
        self.assertEqual(reloaded['revision'], original['revision'] + 1)
        self.assertEqual(self.lab.sql(self.db, 'SELECT count(*) FROM inventory_connection'), '623')
        server.close()

    def test_transaction_rollback_retry_and_existing_destination_denied(self):
        house = self.lab.sql(self.db, 'SELECT name FROM systemhaus', sensitive=True)
        self.lab.sql(self.db, """CREATE FUNCTION reject_restore_audit() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
          IF NEW.action='laboratory.rc9.restore' THEN RAISE EXCEPTION 'synthetic failure'; END IF; RETURN NEW; END $$;
          CREATE TRIGGER reject_restore_audit BEFORE INSERT ON audit_event FOR EACH ROW EXECUTE FUNCTION reject_restore_audit();""")
        self.error(lambda: restore_module.restore(self.lab, self.db, SOURCE, self.actor), 'restore_transaction_rejected')
        for table in restore_module.TABLES:
            self.assertEqual(self.lab.sql(self.db, f'SELECT count(*) FROM {table}'), '0')
        self.assertEqual(self.lab.sql(self.db, 'SELECT count(*) FROM audit_event'), '0')
        self.assertEqual(self.lab.sql(self.db, 'SELECT revision FROM systemhaus'), '1')
        self.check(self.lab.sql(self.db, 'SELECT name FROM systemhaus', sensitive=True) == house, 'Rollback must retain house name')
        self.assertEqual(self.lab.sql(self.db, "SELECT count(*) FROM pg_namespace WHERE nspname='laboratory_restore'"), '0')
        self.lab.sql(self.db, 'DROP TRIGGER reject_restore_audit ON audit_event')
        self.check(restore_module.restore(self.lab, self.db, SOURCE, self.actor)['committed'], 'Retry after rollback must commit')
        self.error(lambda: restore_module.restore(self.lab, self.db, SOURCE, self.actor), 'restore_destination_not_empty')
        self.assertEqual(self.lab.sql(self.db, 'SELECT count(*) FROM customer'), '10')
        self.assertEqual(self.lab.sql(self.db, 'SELECT count(*) FROM inventory_connection'), '623')
        self.assertEqual(self.lab.sql(self.db, "SELECT count(*) FROM audit_event WHERE action='laboratory.rc9.restore'"), '1')

    def test_malformed_and_incompatible_sources_leave_database_empty(self):
        source = json.loads(SOURCE.read_text(encoding='utf-8-sig'))
        variants = [
            ('source_version_unsupported', lambda x: x.update(version='unknown')),
            ('port_type_invalid', lambda x: x['racks'][0]['devs'][0]['ports'][0].update(type='unknown')),
            ('port_type_invalid', lambda x: x['racks'][0]['devs'][0]['ports'][0].update(type=[])),
            ('port_status_invalid', lambda x: x['racks'][0]['devs'][0]['ports'][0].update(status='unknown')),
            ('watts_invalid', lambda x: x['racks'][0]['devs'][0]['ports'][0].update(watts=91)),
            ('port_face_invalid', lambda x: x['racks'][0]['devs'][0]['ports'][0].update(rackclickFace='unknown')),
            ('original_id_duplicate', lambda x: x['racks'][0]['devs'][0]['ports'].append(copy.deepcopy(x['racks'][0]['devs'][0]['ports'][0]))),
            ('group_ambiguous', lambda x: x['racks'][0]['devs'][0]['ports'][1].update(gn=x['racks'][0]['devs'][0]['ports'][0]['gn'])),
            ('group_definition_unsupported', lambda x: x['racks'][0]['devs'][0].update(portGroups=[])),
            ('connection_dangling', lambda x: x['racks'][0]['conns'][0].update(fp='missing-private-source-id')),
            ('rack_capacity_exceeded', lambda x: x['racks'][0].update(size=1)),
            ('patch_invalid', lambda x: x['racks'][0]['conns'][0].update(patchStatus='unknown')),
            ('connection_port_blocked', lambda x: next(p for r in x['racks'] for d in r['devs'] for p in d['ports'] if p['id']==x['racks'][0]['conns'][0]['fp']).update(status='disabled')),
        ]
        for number, (code, change) in enumerate(variants):
            with self.subTest(code=code):
                value = copy.deepcopy(source)
                change(value)
                path = self.db.directory / f'negative-{number}.json'
                path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
                self.error(lambda: restore_module.restore(self.lab, self.db, path, self.actor), code)
        # Make one endpoint refer to a real different customer's port and correct
        # its device owner so customer separation, not dangling detection, rejects.
        value = copy.deepcopy(source)
        foreign = next(r for r in value['racks'] if r['rackclickLocation']['client'] != value['racks'][0]['rackclickLocation']['client'])
        value['racks'][0]['conns'][0].update(fp=foreign['devs'][0]['ports'][0]['id'], fd=foreign['devs'][0]['id'])
        path = self.db.directory / 'negative-cross-customer.json'
        path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
        self.error(lambda: restore_module.restore(self.lab, self.db, path, self.actor), 'connection_cross_customer')
        path = self.db.directory / 'negative-duplicate-key.json'
        path.write_text('{"version":"0.8","version":"0.8"}', encoding='utf-8')
        self.error(lambda: restore_module.restore(self.lab, self.db, path, self.actor), 'duplicate_json_key')
        path = self.db.directory / 'negative-json.json'
        path.write_text('{', encoding='utf-8')
        self.error(lambda: restore_module.restore(self.lab, self.db, path, self.actor), 'json_invalid')
        # Missing/explicit PoE follow RC9 semantics; no normalization or silent
        # correction of invalid supplied attributes occurs during restoration.
        value = copy.deepcopy(source)
        legacy = next(p for r in value['racks'] for d in r['devs'] for p in d['ports'] if p['type']=='rj45_poe')
        legacy.pop('poe', None)
        path = self.db.directory / 'legacy-poe-default.json'
        path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
        plan = restore_module.analyze(path)
        mapped = restore_module.ident('ports', legacy['id'])
        self.check(next(p for p in plan['rows']['inventory_port'] if p['id']==mapped)['poe'] is True,
                   'Legacy rj45_poe without explicit flag must preserve RC9 enabled default')
        legacy['poe'] = False
        path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
        plan = restore_module.analyze(path)
        self.check(next(p for p in plan['rows']['inventory_port'] if p['id']==mapped)['poe'] is False,
                   'Explicit legacy PoE false must be preserved')
        self.assertEqual(self.lab.sql(self.db, 'SELECT count(*) FROM customer'), '0')
        self.assertEqual(self.lab.sql(self.db, 'SELECT count(*) FROM inventory_port'), '0')
        self.assertEqual(self.lab.sql(self.db, 'SELECT count(*) FROM audit_event'), '0')
        self.assertEqual(self.lab.sql(self.db, 'SELECT revision FROM systemhaus'), '1')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--case')
    args = parser.parse_args()
    args.evidence.mkdir(parents=True, exist_ok=False)
    source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    importer = WORKSPACE / 'tools/windows/rc9_restore.py'
    test_source = Path(__file__)
    data = {'utc': datetime.now(timezone.utc).isoformat(), 'platform': platform.platform(),
            'dllSha256': hashlib.sha256(DEFAULT_DLL.read_bytes()).hexdigest(), 'sourceSha256': source_hash,
            'importerSha256': hashlib.sha256(importer.read_bytes()).hexdigest(),
            'testSha256': hashlib.sha256(test_source.read_bytes()).hexdigest()}
    lab = Lab('rc9-restore-tests')
    with lab, (args.evidence / 'tests.log').open('w', encoding='utf-8') as output:
        RestorePostgres.lab = lab
        names = unittest.defaultTestLoader.getTestCaseNames(RestorePostgres)
        if args.case:
            if args.case not in names:
                parser.error('Unknown restore test')
            names = [args.case]
        suite = unittest.TestSuite(RestorePostgres(name) for name in names)
        result = unittest.TextTestRunner(stream=Tee(sys.stdout, output), verbosity=2, resultclass=EvidenceResult).run(suite)
        data.update(testsRun=result.testsRun, cases=result.records, successful=result.wasSuccessful())
    data.update(labStopped=not lab.running,
        inputsUnchanged=data['dllSha256'] == hashlib.sha256(DEFAULT_DLL.read_bytes()).hexdigest()
            and source_hash == hashlib.sha256(SOURCE.read_bytes()).hexdigest()
            and data['importerSha256'] == hashlib.sha256(importer.read_bytes()).hexdigest()
            and data['testSha256'] == hashlib.sha256(test_source.read_bytes()).hexdigest())
    (args.evidence / 'result.json').write_text(json.dumps(data, indent=2), encoding='utf-8')
    return 0 if result.wasSuccessful() and data['labStopped'] and data['inputsUnchanged'] else 1


if __name__ == '__main__':
    sys.exit(main())
