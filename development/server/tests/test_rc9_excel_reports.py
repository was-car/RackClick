"""RC9 Excel HTML reports: frozen candidate, isolated native Windows/PostgreSQL only.

This author suite structurally parses bytes with Python's HTML parser. It does
not claim to open Office or validate Office's formula evaluation behavior.
"""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import platform
import re
import subprocess
import sys
import time
import unittest

from pg_support import Lab, WORKSPACE, NO_WINDOW, literal
from test_postgres import EvidenceResult, Tee
from test_inventory_reports import InventoryReportsPostgres, uid


DEVICE_HEADERS = ['Name', 'Preset', 'Size (U)', 'Ports', 'Connected', 'Icon', 'Color']
CABLE_HEADERS = ['From Device', 'From Port#', 'From Type', 'From Label', 'To Device', 'To Port#',
                 'To Type', 'To Label', 'Cable/Note', 'Cross-Rack', 'Color', 'Created']
SUMMARY_KEYS = ['Rack Name', 'Location', 'Size', 'Used', 'Free', 'Devices', 'Connections', 'Project', 'Technician', 'Exported']


class ReportParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables, self.comments, self.body, self.stack = [], [], None, []
        self.cell = None

    def handle_decl(self, decl):
        assert decl == 'DOCTYPE html', decl

    def handle_comment(self, data):
        self.comments.append(data)

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        assert len(values) == len(attrs)
        assert tag in {'html', 'head', 'meta', 'style', 'body', 'table', 'thead', 'tbody', 'tr', 'td', 'th'}, tag
        if tag == 'body': self.body = values
        elif tag == 'table':
            assert values == {'x:str': '', 'border': '1', 'data-table': ['Devices', 'Connections', 'Summary'][len(self.tables)]}
            self.tables.append([])
        elif tag == 'tr':
            self.tables[-1].append({'attrs': values, 'values': [], 'cellTags': []})
        elif tag in {'th', 'td'}:
            assert set(values) == {'x:str'}
            if tag == 'th': assert values['x:str'] is None
            else: assert isinstance(values['x:str'], str)
            self.cell_attribute = values['x:str']
            self.cell = ''
            self.tables[-1][-1]['cellTags'].append(tag)
        if tag != 'meta': self.stack.append(tag)

    def handle_endtag(self, tag):
        assert self.stack.pop() == tag
        if tag in {'th', 'td'}:
            if tag == 'td': assert self.cell_attribute == self.cell, 'Excel text attribute must equal visible text exactly'
            self.tables[-1][-1]['values'].append(self.cell)
            self.cell = None

    def handle_data(self, data):
        if self.cell is not None: self.cell += data
        else: assert self.stack[-1] == 'style', data


class Rc9ExcelPostgres(InventoryReportsPostgres):
    evidence = None

    def durable(self):
        # The inherited UNION ALL of unlabelled digests has no final ordering;
        # parallel append may reorder it at 10000 rows. Preserve EVERY table and
        # bind its digest to its name before PostgreSQL canonical JSON ordering.
        names = self.lab.sql(self.db, "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename").splitlines()
        parts = [f"SELECT '{name}' AS table_name,md5(COALESCE(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text)::text,'')) AS digest FROM public.\"{name}\" t" for name in names]
        return json.loads(self.lab.sql(self.db, 'SELECT jsonb_object_agg(table_name,digest)::text FROM (' + ' UNION ALL '.join(parts) + ') digests'))

    def generate(self, payload=None, revision=None, key=None, client=None, customer=None, status=200, headers=None):
        customer, client = customer or self.customer_id, client or self.admin
        if revision is None: revision = self.snapshot(customer)['revision']
        if payload is None: payload = {'rackId': self.rack_id}
        response = self.expect(client.request('POST', f'/api/v1/customers/{customer}/reports/xls-html', payload,
            {'If-Match': f'"{revision}"', 'Idempotency-Key': key or uid(), 'X-RackClick-Actor': client.actor_id, **(headers or {})}), status)
        if status != 200: return response
        value = response.json()
        self.assertEqual(set(value), {'kind', 'customerId', 'revision', 'requestId', 'operationId', 'report'})
        self.assertEqual((value['kind'], value['customerId'], value['revision']), ('rc9ExcelReport', customer, revision))
        self.assertEqual(response.headers['etag'], f'"{revision}"')
        self.xls(value)
        return value

    def report_status(self, key, client=None, customer=None, status=200):
        customer = customer or self.customer_id
        response = self.expect((client or self.admin).request('GET',
            f'/api/v1/customers/{customer}/reports/xls-html/operations/{key}'), status)
        if status != 200: return response
        value = response.json()
        self.assertEqual(set(value), {'state', 'customerId', 'requestId', 'operation'})
        self.assertEqual((value['customerId'], value['requestId']), (customer, key))
        if value['operation'] is not None: self.xls(value['operation'])
        return value

    def xls(self, result):
        r = result['report']
        self.assertEqual(set(r), {'format', 'cellEncoding', 'rackId', 'generatedAt', 'filename', 'contentType',
            'deviceCount', 'connectionCount', 'summaryCount', 'rowCount', 'byteLength', 'sha256', 'contentBase64'})
        self.assertEqual((r['format'], r['cellEncoding'], r['contentType']),
            ('xls-html-rc9-v1', 'html-text-v1', 'application/vnd.ms-excel;charset=utf-8'))
        self.assertRegex(r['generatedAt'], r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$')
        self.assertEqual(r['filename'], f'rackclick-rack-{r["rackId"]}-r{result["revision"]}.xls')
        raw = base64.b64decode(r['contentBase64'], validate=True)
        self.assertEqual(base64.b64encode(raw).decode(), r['contentBase64'])
        self.assertEqual((len(raw), hashlib.sha256(raw).hexdigest()), (r['byteLength'], r['sha256']))
        self.assertLessEqual(len(raw), 4194304)
        self.assertFalse(raw.startswith(b'\xef\xbb\xbf'))
        parser = ReportParser()
        parser.feed(raw.decode('utf-8', errors='strict'))
        parser.close()
        self.assertEqual(parser.stack, [])
        self.assertEqual(parser.body, {'data-format': 'xls-html-rc9-v1', 'data-customer-id': result['customerId'],
            'data-rack-id': r['rackId'], 'data-revision': str(result['revision'])})
        self.assertEqual(len(parser.comments), 1)
        self.assertTrue(parser.comments[0].startswith('[if gte mso 9]><xml><x:ExcelWorkbook>'))
        for name in ['Devices', 'Connections', 'Summary']:
            self.assertIn(f'<x:Name>{name}</x:Name>', parser.comments[0])
        rows = []
        for table, columns in zip(parser.tables, [DEVICE_HEADERS, CABLE_HEADERS, ['Property', 'Value']]):
            self.assertEqual(table[0], {'attrs': {}, 'values': columns, 'cellTags': ['th'] * len(columns)})
            for row in table[1:]:
                self.assertEqual(row['cellTags'], ['td'] * len(columns))
                self.assertEqual(len(row['values']), len(columns))
            rows.append(table[1:])
        self.assertEqual([len(t) for t in rows], [r['deviceCount'], r['connectionCount'], 10])
        self.assertEqual(r['rowCount'], r['deviceCount'] + r['connectionCount'] + 10)
        self.assertLessEqual(r['rowCount'], 10000)
        self.assertEqual([row['values'][0] for row in rows[2]], SUMMARY_KEYS)
        self.assertEqual(rows[2][-1]['values'], ['Exported', r['generatedAt']])
        self.assertEqual(rows[2][-2]['values'], ['Technician', ''])
        return rows, raw

    def fixture(self):
        values = super().fixture()
        self.rack_id = values[3]['id']
        return values

    def test_projection_literal_source_groups_intra_cross_room_and_office_fixture(self):
        _, _, room, rack, device, groups, ports, dose, dp, cable = self.fixture()
        _, _, _, rack2 = self.hierarchy('Second')
        second, _, sp = self.device('Other rack device', rack=rack2['id'])
        extra, eg, ep = self.device('+1+1', rack=rack['id'], groups=[{'type': 'rj45', 'count': 2}, {'type': 'rj45', 'count': 2}], size=2)
        intra = self.connect(ports[2], ports[3])
        endpoint = lambda group, gn: next(p for p in ep if p['groupId'] == group['id'] and p['gn'] == gn)
        repeated = self.connect(endpoint(eg[0], 1), endpoint(eg[1], 1), note='-2+3')
        cross = self.connect(endpoint(eg[0], 2), sp[0], note='@SUM(1,2)')
        self.lab.sql(self.db, f"UPDATE inventory_device SET name='=1+1',properties='{{\"preset\":\"000001\",\"icon\":\"Ω 日本語 🐈\",\"color\":\"#12aBcD\"}}' WHERE id='{device['id']}'")
        self.lab.sql(self.db, f"UPDATE inventory_port SET label='000001' WHERE id='{ports[0]['id']}'")
        self.lab.sql(self.db, f"UPDATE inventory_connection SET properties='{{\"fn\":\"WRONG OLD NAME\",\"created\":\"WRONG OLD CREATED\",\"createdAt\":\"legacy literal 😃\\t\\r\\n\"}}' WHERE id='{cable['id']}'")
        before = self.stable_inventory()
        made = self.generate()
        tables, raw = self.xls(made)
        by_device = {r['attrs']['data-device-id']: r['values'] for r in tables[0]}
        self.assertEqual(set(by_device), {device['id'], extra['id']})
        self.assertEqual(by_device[device['id']], ['=1+1', '000001', '1', '4', '2', 'Ω 日本語 🐈', '#12aBcD'])
        self.assertEqual(by_device[extra['id']][2:5], ['2', '4', '2'])
        by_cable = {r['attrs']['data-connection-id']: r for r in tables[1]}
        self.assertEqual(set(by_cable), {cable['id'], intra['id'], repeated['id'], cross['id']})
        self.assertEqual(by_cable[intra['id']]['values'][9], '')
        self.assertEqual(by_cable[cross['id']]['values'][9], rack['name'] + ' → ' + rack2['name'])
        self.assertEqual(by_cable[cable['id']]['values'][9], f"{rack['name']} → Room: {room['name']} [{room['id']}] / {dose['name']}")
        self.assertEqual(by_cable[cable['id']]['values'][0:4], ['=1+1', '1', 'rj45', '000001'])
        self.assertEqual(by_cable[cable['id']]['values'][11], 'legacy literal 😃\t\r\n')
        rr = by_cable[repeated['id']]
        self.assertEqual(rr['values'][1], rr['values'][5])
        self.assertNotEqual(rr['attrs']['data-from-group-id'], rr['attrs']['data-to-group-id'])
        self.assertEqual(rr['attrs']['data-from-group-type'], 'rj45')
        self.assertEqual([r['values'] for r in tables[2]][2:7], [['Size', '42U'], ['Used', '3U'], ['Free', '39U'], ['Devices', '2'], ['Connections', '4']])
        self.assertNotIn(b'WRONG OLD', raw)
        self.assertEqual(before, self.stable_inventory())
        (self.evidence / 'office-fixture.xls').write_bytes(raw)
        (self.evidence / 'office-fixture.json').write_text(json.dumps({'source': 'new isolated synthetic PostgreSQL fixture',
            'report': made['report'], 'tables': tables, 'expectedTextValues': ['=1+1', '+1+1', '-2+3', '@SUM(1,2)', '000001', 'Ω 日本語 🐈'],
            'officeOpenedByThisTest': False}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    def test_unicode_limits_created_fallback_and_source_invalid(self):
        _, _, _, rack, device, _, ports, _, _, cable = self.fixture()
        legacy = '=1+1\t\r\n&<>\"\' 😃'
        self.lab.sql(self.db, f"UPDATE inventory_connection SET properties={literal(json.dumps({'createdAt': legacy}))}::jsonb WHERE id='{cable['id']}'")
        self.assertEqual(self.xls(self.generate())[0][1][0]['values'][11], legacy)
        for props in [{}, {'createdAt': None, 'created': 'never-use-this'}]:
            self.lab.sql(self.db, f"UPDATE inventory_connection SET created_at='2001-02-03T04:05:06.123Z',properties={literal(json.dumps(props))}::jsonb WHERE id='{cable['id']}'")
            self.assertEqual(self.xls(self.generate())[0][1][0]['values'][11], '2001-02-03T04:05:06.123Z')
        for value in [42, True, [], {}]:
            self.lab.sql(self.db, f"UPDATE inventory_connection SET properties={literal(json.dumps({'createdAt': value}))}::jsonb WHERE id='{cable['id']}'")
            before = self.durable()
            self.expect(self.generate(status=422), 422, 'report_source_invalid')
            self.assertEqual(self.durable(), before)
        self.lab.sql(self.db, f"UPDATE inventory_connection SET properties='{{}}' WHERE id='{cable['id']}'")
        text = '😃' * 16383 + 'A'
        self.lab.sql(self.db, f"UPDATE inventory_device SET properties=jsonb_build_object('preset',{literal(text)}) WHERE id='{device['id']}'")
        self.assertEqual(self.xls(self.generate())[0][0][0]['values'][1], text)
        self.lab.sql(self.db, f"UPDATE inventory_device SET properties=jsonb_set(properties,'{{preset}}',to_jsonb((properties->>'preset')||'B')) WHERE id='{device['id']}'")
        before = self.durable()
        self.expect(self.generate(status=422), 422, 'report_too_large')
        self.assertEqual(self.durable(), before)
        for text in ['bad\x01', 'bad\x7f', 'bad\x85', 'bad\uffff']:
            self.lab.sql(self.db, f"UPDATE inventory_device SET properties=jsonb_build_object('preset',{literal(text)}) WHERE id='{device['id']}'")
            before = self.durable()
            self.expect(self.generate(status=422), 422, 'report_cell_invalid')
            self.assertEqual(self.durable(), before)
        self.lab.sql(self.db, f"UPDATE inventory_device SET properties='{{}}' WHERE id='{device['id']}'")
        # Simulate damaged imported storage in this disposable owner's database only.
        self.lab.sql(self.db, f"SET session_replication_role=replica; DELETE FROM inventory_connection_endpoint WHERE connection_id='{cable['id']}' AND ordinal=1; SET session_replication_role=origin", admin=True)
        before = self.durable()
        self.expect(self.generate(status=422), 422, 'report_source_invalid')
        self.assertEqual(self.durable(), before)

    def test_closed_dto_headers_csrf_and_total_rows_bytes_empty(self):
        _, _, _, rack, device, _, _, _, _, _ = self.fixture()
        valid = {'rackId': rack['id']}
        for payload in [{}, {'rackId': None}, {'rackId': 'not-id'}, {'rackId': '00000000-0000-0000-0000-000000000000'},
                        {**valid, 'query': ''}, {**valid, 'language': 'es'}, {**valid, 'status': 'all'}]:
            before = self.durable()
            self.expect(self.generate(payload, status=422), 422, 'request_invalid')
            self.assertEqual(self.durable(), before)
        self.expect(self.generate(b'{"rackId":"' + rack['id'].encode() + b'","rackId":"' + rack['id'].encode() + b'"}',
            status=422, headers={'Content-Type': 'application/json'}), 422, 'request_invalid')
        for headers, status, code in [({'X-RackClick-CSRF': 'bad'}, 403, 'csrf_invalid'),
            ({'Origin': 'https://foreign.invalid'}, 403, 'origin_invalid'), ({'X-RackClick-Actor': ''}, 422, 'actor_invalid'),
            ({'If-Match': ''}, 428, 'revision_required'), ({'Idempotency-Key': 'bad'}, 422, 'request_id_invalid')]:
            self.expect(self.generate(status=status, headers=headers), status, code)
        self.expect(self.generate({'rackId': uid()}, status=404), 404, 'not_found')
        revision = self.snapshot()['revision']
        headers = {'If-Match': f'"{revision}"', 'Idempotency-Key': uid(), 'X-RackClick-Actor': self.admin_id}
        self.expect(self.admin.request('POST', f'/api/v1/customers/{self.customer_id}/reports/xls-html?status=all', valid, headers), 422, 'request_invalid')
        _, _, _, empty = self.hierarchy('Empty')
        made = self.generate({'rackId': empty['id']})
        self.assertEqual((made['report']['deviceCount'], made['report']['connectionCount'], made['report']['rowCount']), (0, 0, 10))
        # Exactly 10000 data rows (including one cable and ten Summary) then one above.
        self.lab.sql(self.db, f"INSERT INTO inventory_device(id,systemhaus_id,customer_id,kind,rack_id,name,size_u,sort_order) SELECT gen_random_uuid(),'{self.house_id}','{self.customer_id}','rackEquipment','{rack['id']}','Bulk',1,10000+g FROM generate_series(1,9988) g")
        self.assertEqual(self.generate()['report']['rowCount'], 10000)
        self.lab.sql(self.db, f"INSERT INTO inventory_device(id,systemhaus_id,customer_id,kind,rack_id,name,size_u,sort_order) VALUES(gen_random_uuid(),'{self.house_id}','{self.customer_id}','rackEquipment','{rack['id']}','Above',1,30000)")
        before = self.durable()
        self.expect(self.generate(status=422), 422, 'report_too_large')
        after = self.durable()
        (self.evidence / 'rejected-10001-state.json').write_text(json.dumps({'before': before, 'after': after,
            'allTablesRetained': True, 'equal': before == after}, indent=2) + '\n', encoding='utf-8')
        self.assertEqual(after, before)
        self.lab.sql(self.db, 'DELETE FROM inventory_device WHERE sort_order>=10000')
        self.lab.sql(self.db, f"INSERT INTO inventory_device(id,systemhaus_id,customer_id,kind,rack_id,name,size_u,sort_order,properties) SELECT gen_random_uuid(),'{self.house_id}','{self.customer_id}','rackEquipment','{rack['id']}','Bulk bytes',1,10000+g,jsonb_build_object('preset',repeat('é',2000)) FROM generate_series(1,1100) g")
        before = self.durable()
        self.expect(self.generate(status=422), 422, 'report_too_large')
        self.assertEqual(self.durable(), before)

    def test_permissions_scope_other_actor_formats_and_generic_denials(self):
        self.fixture()
        made = self.generate()
        key, revision = made['requestId'], made['revision']
        reader, _, _ = self.add_user('xls-reader', ['inventory.read'], self.customer_id)
        export_only, _, _ = self.add_user('xls-export-only', ['reports.export'], self.customer_id)
        other, _, _ = self.add_user('xls-other', ['inventory.read', 'reports.export'], self.customer_id)
        self.expect(self.generate(client=reader, status=403), 403, 'forbidden')
        self.expect(self.report_status(key, client=reader, status=403), 403, 'forbidden')
        self.expect(self.report_status(key, client=export_only, status=404), 404, 'not_found')
        self.assertEqual(self.report_status(key, client=other)['state'], 'notRecorded')
        self.assertEqual(self.generate(client=other)['kind'], 'rc9ExcelReport')
        customer = self.customer('Foreign scope')['id']
        self.expect(self.report_status(key, customer=customer, status=404), 404, 'not_found')
        self.expect(self.report_status(uid(), customer=customer, client=other, status=404), 404, 'not_found')
        self.expect(InventoryReportsPostgres.report_status(self, key, status=404), 404, 'not_found')
        headers = {'If-Match': f'"{revision}"', 'Idempotency-Key': uid(), 'X-RackClick-Actor': self.admin_id}
        csv = self.expect(self.admin.request('POST', f'/api/v1/customers/{self.customer_id}/reports/csv', self.request(), headers), 200).json()
        self.expect(self.report_status(csv['requestId'], status=404), 404, 'not_found')
        self.lab.sql(self.db, "DELETE FROM permission_grant WHERE capability='reports.export' AND user_group_id IN "
            f"(SELECT group_id FROM user_group_member WHERE user_id='{self.admin_id}')")
        before = self.durable()
        self.expect(self.generate(key=key, revision=revision, status=403), 403, 'forbidden')
        self.expect(self.report_status(key, status=403), 403, 'forbidden')
        path = f'/api/v1/customers/{self.customer_id}/operations/{key}'
        self.expect(self.admin.request('GET', path), 404, 'not_found')
        self.command('site.create', {'name': 'Must not create'}, key=key, status=404)
        self.expect(self.admin.request('POST', path + '/cancel', {'type': 'site.create', 'payload': {'name': 'Must not create'}},
            {**headers, 'Idempotency-Key': key}), 404, 'not_found')
        house_revision = self.lab.sql(self.db, 'SELECT revision FROM systemhaus')
        self.expect(self.admin.request('PUT', '/api/v1/systemhaus', {'name': 'Must not rename'},
            {**headers, 'If-Match': f'"{house_revision}"', 'Idempotency-Key': key}), 404, 'not_found')
        state = self.expect(self.admin.request('GET', f'/api/v1/admin/users/operations/{key}'), 200).json()
        self.assertEqual((state['state'], state['operation']), ('notRecorded', None))
        self.assertEqual(self.durable(), before)

    def test_replay_revision_concurrency_bytes_and_restart(self):
        self.fixture()
        revision, key = self.snapshot()['revision'], uid()
        before = self.stable_inventory()
        with ThreadPoolExecutor(2) as pool:
            futures = [pool.submit(self.generate, revision=revision, key=key) for _ in range(2)]
            a, b = [f.result(timeout=30) for f in futures]
        self.assertEqual(a, b)
        self.assertEqual(self.stable_inventory(), before)
        self.assertEqual(self.lab.sql(self.db, f"SELECT count(*) FROM audit_event WHERE request_id='{key}'"), '1')
        self.command('site.create', {'name': 'Advance source'})
        self.assertEqual(self.generate(revision=revision, key=key), a)
        self.expect(self.generate(revision=revision, status=412), 412, 'revision_conflict')
        self.expect(self.generate(key=key, status=409), 409, 'request_id_reused')
        self.assertEqual(self.report_status(key)['operation'], a)
        self.assertEqual(self.report_status(uid())['state'], 'notRecorded')
        self.server.close()
        self.server = self.lab.start_server(self.db, dll=self.dll, frontend=self.frontend)
        self.admin.server = self.server
        self.assertEqual(self.report_status(key)['operation'], a)
        self.assertEqual(self.generate(revision=revision, key=key), a)

    def test_revocation_expiry_and_request_wait_rechecks(self):
        self.fixture()
        for cap, status, code in [('inventory.read', 404, 'not_found'), ('reports.export', 403, 'forbidden')]:
            reader, group, _ = self.add_user('xls-revoke-' + cap, ['inventory.read', 'reports.export'], self.customer_id)
            self.waiting_report(reader, lambda: self.lab.sql(self.db,
                f"DELETE FROM permission_grant WHERE user_group_id='{group}' AND capability={literal(cap)}"), status, code)
        reader, _, _ = self.add_user('xls-expire', ['inventory.read', 'reports.export'], self.customer_id)
        self.lab.sql(self.db, f"UPDATE app_session SET expires_at=clock_timestamp()+interval '2 seconds' WHERE user_id='{reader.actor_id}'")
        self.waiting_report(reader, lambda: None, 401, 'authentication_required', table='app_user', identity=reader.actor_id)
        self.expect(reader.login('xls-expire', self.password), 200)
        self.waiting_report(reader, lambda: self.lab.sql(self.db, f"DELETE FROM app_session WHERE user_id='{reader.actor_id}'"), 401, 'authentication_required')
        self.expect(reader.login('xls-expire', self.password), 200)
        key, revision = uid(), self.snapshot()['revision']
        label = 'xlskey_' + uid()
        lock_key = f'RackClick/operation/{self.house_id}/{reader.actor_id}/{key}'
        with ThreadPoolExecutor(2) as pool:
            holding = pool.submit(self.lab.sql, self.db, f"SET application_name='{label}'; BEGIN; SELECT pg_advisory_xact_lock(hashtextextended({literal(lock_key)},0)); SELECT pg_sleep(3); COMMIT")
            self.wait_for(f"SELECT count(*) FROM pg_stat_activity WHERE application_name='{label}' AND wait_event='PgSleep'")
            pending = pool.submit(self.generate, client=reader, key=key, revision=revision, status=401)
            self.wait_for(f"SELECT count(*) FROM pg_stat_activity WHERE datname='{self.db.name}' AND cardinality(pg_blocking_pids(pid))>0")
            self.lab.sql(self.db, f"DELETE FROM app_session WHERE user_id='{reader.actor_id}'")
            self.expect(pending.result(timeout=15), 401, 'authentication_required')
            holding.result(timeout=10)

    def test_rollback_audit_revision_feed_and_openapi(self):
        self.fixture()
        for table in ['audit_event', 'operation']:
            predicate = "NEW.action='reports.xlsHtml.generate'" if table == 'audit_event' else "NEW.result_json->>'kind'='rc9ExcelReport'"
            self.lab.sql(self.db, f"CREATE FUNCTION fail_xls() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF {predicate} THEN RAISE EXCEPTION 'synthetic XLS rollback' USING ERRCODE='23514'; END IF; RETURN NEW; END $$; CREATE TRIGGER fail_xls BEFORE INSERT ON {table} FOR EACH ROW EXECUTE FUNCTION fail_xls()")
            before, key = self.durable(), uid()
            self.expect(self.generate(key=key, status=409), 409, 'report_conflict')
            self.assertEqual(self.durable(), before)
            self.assertEqual(self.report_status(key)['state'], 'notRecorded')
            self.lab.sql(self.db, f'DROP TRIGGER fail_xls ON {table}; DROP FUNCTION fail_xls()')
        revision = self.snapshot()['revision']
        before = self.stable_inventory()
        made = self.generate()
        self.assertEqual(self.stable_inventory(), before)
        event = json.loads(self.lab.sql(self.db, f"SELECT row_to_json(a) FROM audit_event a WHERE id='{made['operationId']}'"))
        self.assertEqual(event['action'], 'reports.xlsHtml.generate')
        self.assertEqual(event['after_json']['sourceRevision'], revision)
        self.assertEqual(event['after_json']['sha256'], made['report']['sha256'])
        self.assertNotIn('contentBase64', json.dumps(event))
        self.assertNotIn('properties', json.dumps(event))
        self.assertEqual(self.poll(revision)['events'], [])
        self.assertEqual(self.snapshot()['revision'], revision)
        doc = self.expect(self.admin.request('GET', '/api/v1/openapi.json'), 200).json()
        self.assertIn('/api/v1/customers/{id}/reports/xls-html', doc['paths'])
        self.assertIn('/api/v1/customers/{id}/reports/xls-html/operations/{requestId}', doc['paths'])
        schemas = doc['components']['schemas']
        for name in ['Rc9ExcelRequest', 'Rc9ExcelReport', 'Rc9ExcelResult', 'Rc9ExcelStatus']:
            self.assertFalse(schemas[name]['additionalProperties'])
        self.assertEqual(schemas['Rc9ExcelResult']['properties']['kind']['enum'], ['rc9ExcelReport'])
        reader, _, _ = self.add_user('xls-expire-commit', ['inventory.read', 'reports.export'], self.customer_id)
        self.lab.sql(self.db, "CREATE FUNCTION slow_xls() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.action='reports.xlsHtml.generate' THEN PERFORM pg_sleep(3); END IF; RETURN NEW; END $$; CREATE TRIGGER slow_xls BEFORE INSERT ON audit_event FOR EACH ROW EXECUTE FUNCTION slow_xls()")
        self.lab.sql(self.db, f"UPDATE app_session SET expires_at=clock_timestamp()+interval '2 seconds' WHERE user_id='{reader.actor_id}'")
        before = self.durable()
        self.expect(self.generate(client=reader, status=401), 401, 'authentication_required')
        self.assertEqual(self.durable(), before)


def distribution(path):
    return {p.relative_to(path).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(path.rglob('*')) if p.is_file()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['dll', 'frontend', 'evidence']: parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--case', action='append', required=True)
    args = parser.parse_args()
    available = [n for n in Rc9ExcelPostgres.__dict__ if n.startswith('test_')]
    if set(args.case) - set(available): raise ValueError('Unknown RC9 Excel case')
    names = [n for n in available if n in args.case]
    args.dll, args.frontend, args.evidence = args.dll.resolve(), args.frontend.resolve(), args.evidence.resolve()
    args.evidence.mkdir(parents=True, exist_ok=False)
    files = [p for p in (WORKSPACE / 'development/server/src').rglob('*.cs') if 'obj' not in p.parts and 'bin' not in p.parts]
    files += list((WORKSPACE / 'development/server/database').glob('*.sql'))
    files += [Path(__file__).resolve()] + [WORKSPACE / 'development/server/tests' / n for n in
        ['pg_support.py', 'test_postgres.py', 'test_inventory_reports.py', 'test_inventory_changes.py',
         'test_inventory_postgres.py', 'test_inventory_read_views.py', 'test_admin_grants.py']]
    def sources(): return {p.relative_to(WORKSPACE).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    original, server, frontend = sources(), distribution(args.dll.parent), distribution(args.frontend)
    report = {'utc': datetime.now(timezone.utc).isoformat(), 'platform': platform.platform(), 'python': platform.python_version(),
        'serverPath': str(args.dll.parent), 'frontendPath': str(args.frontend), 'serverHashes': server, 'frontendHashes': frontend,
        'sourceHashes': original, 'selectedCases': names, 'schemaVersion': 11, 'actualQaOpened': False,
        'excelOrLibreOfficeOpened': False}
    (args.evidence / 'inputs-before.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    copies = args.evidence / 'sources-before'
    for relative in original:
        target = copies / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((WORKSPACE / relative).read_bytes())
    lab = Lab('rc9-excel-html')
    Rc9ExcelPostgres.lab, Rc9ExcelPostgres.evidence = lab, args.evidence
    Rc9ExcelPostgres.dll, Rc9ExcelPostgres.frontend = args.dll, args.frontend
    report['versions'] = {name: subprocess.run([str(path), '--version'], capture_output=True, text=True,
        check=True, creationflags=NO_WINDOW).stdout.strip()
        for name, path in [('dotnet', lab.dotnet), ('postgres', lab.pg_bin / 'postgres.exe')]}
    started = time.monotonic()
    with lab, (args.evidence / 'tests.log').open('w', encoding='utf-8') as output:
        result = unittest.TextTestRunner(stream=Tee(sys.stdout, output), verbosity=2, resultclass=EvidenceResult).run(
            unittest.TestSuite(Rc9ExcelPostgres(n) for n in names))
        report.update(testsRun=result.testsRun, cases=result.records, successful=result.wasSuccessful())
    report.update(elapsedSeconds=round(time.monotonic() - started, 3), labStopped=not lab.running,
        serversStopped=all(s.process.poll() is not None for s in lab.servers), sourcesUnchanged=original == sources(),
        serverUnchanged=server == distribution(args.dll.parent), frontendUnchanged=frontend == distribution(args.frontend))
    (args.evidence / 'result.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return 0 if all(report[k] for k in ['successful', 'labStopped', 'serversStopped', 'sourcesUnchanged', 'serverUnchanged', 'frontendUnchanged']) else 1


if __name__ == '__main__': sys.exit(main())
