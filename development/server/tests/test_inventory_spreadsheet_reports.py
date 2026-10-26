"""Bounded XLSX reports against frozen artifacts and fresh native PostgreSQL labs.

The standard-library ZIP and XML parsers independently inspect generated packages.
This is structural validation, not a claim that Excel/LibreOffice was opened.
"""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import platform
import re
import subprocess
import sys
import time
import unittest
import zipfile
import xml.etree.ElementTree as ET

from pg_support import Lab, WORKSPACE, NO_WINDOW, literal
from test_postgres import EvidenceResult, Tee
from test_inventory_reports import InventoryReportsPostgres, PORT_COLUMNS, uid


NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
REL = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
PKG = 'http://schemas.openxmlformats.org/package/2006/relationships'
CT = 'http://schemas.openxmlformats.org/package/2006/content-types'
PARTS = ['[Content_Types].xml', '_rels/.rels', 'xl/workbook.xml',
         'xl/_rels/workbook.xml.rels', 'xl/worksheets/sheet1.xml']
MIME = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


def decode_cell(value):
    # One pass matters: _x005F_x0041_ means literal _x0041_, not A.
    decoded = re.sub(r'_x([0-9A-Fa-f]{4})_', lambda m: chr(int(m[1], 16)), value)
    return decoded.encode('utf-16-le', errors='surrogatepass').decode('utf-16-le')


class InventorySpreadsheetPostgres(InventoryReportsPostgres):
    def generate(self, payload=None, revision=None, key=None, client=None, customer=None, status=200, headers=None):
        customer = customer or self.customer_id
        client = client or self.admin
        if revision is None:
            revision = self.snapshot(customer)['revision']
        response = self.expect(client.request('POST', f'/api/v1/customers/{customer}/reports/xlsx',
            payload if payload is not None else self.request(),
            {'If-Match': f'"{revision}"', 'Idempotency-Key': key or uid(),
             'X-RackClick-Actor': client.actor_id, **(headers or {})}), status)
        if status != 200:
            return response
        result = response.json()
        self.assertEqual(set(result), {'kind', 'customerId', 'revision', 'requestId', 'operationId', 'report'})
        self.assertEqual(result['kind'], 'spreadsheetReport')
        self.assertEqual(result['customerId'], customer)
        self.assertEqual(result['revision'], revision)
        self.assertEqual(response.headers['etag'], f'"{revision}"')
        self.xlsx(result)
        return result

    def report_status(self, key, client=None, customer=None, status=200):
        customer = customer or self.customer_id
        response = self.expect((client or self.admin).request('GET',
            f'/api/v1/customers/{customer}/reports/xlsx/operations/{key}'), status)
        if status != 200:
            return response
        value = response.json()
        self.assertEqual(set(value), {'state', 'customerId', 'requestId', 'operation'})
        self.assertEqual(value['customerId'], customer)
        self.assertEqual(value['requestId'], key)
        if value['operation'] is not None:
            self.xlsx(value['operation'])
        return value

    def xlsx(self, result):
        report = result['report']
        self.assertEqual(set(report), {'reportKind', 'query', 'status', 'family', 'rackId',
            'filename', 'contentType', 'format', 'cellEncoding', 'rowCount', 'byteLength', 'sha256', 'contentBase64'})
        self.assertEqual(report['contentType'], MIME)
        self.assertEqual(report['format'], 'xlsx')
        self.assertEqual(report['cellEncoding'], 'inline-string-v1')
        self.assertEqual(report['filename'],
            f'rackclick-{report["reportKind"]}-{result["customerId"]}-r{result["revision"]}.xlsx')
        raw = base64.b64decode(report['contentBase64'], validate=True)
        self.assertEqual(len(raw), report['byteLength'])
        self.assertLessEqual(len(raw), 4194304)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), report['sha256'])
        with zipfile.ZipFile(io.BytesIO(raw)) as package:
            self.assertEqual(package.namelist(), PARTS)
            self.assertEqual(package.comment, b'')
            self.assertIsNone(package.testzip())
            total = 0
            for info in package.infolist():
                self.assertEqual(info.compress_type, zipfile.ZIP_STORED)
                self.assertEqual(info.compress_size, info.file_size)
                self.assertEqual(info.date_time, (1980, 1, 1, 0, 0, 0))
                self.assertEqual(info.extra, b'')
                self.assertEqual(info.comment, b'')
                self.assertEqual(info.flag_bits & 9, 0, 'No encryption or streaming descriptors')
                total += info.file_size
            self.assertLessEqual(total, 4194304)
            xml = {name: package.read(name) for name in PARTS}
        for data in xml.values():
            self.assertFalse(data.startswith(b'\xef\xbb\xbf'))
            self.assertNotIn(b'<!', data, 'No DTD, declaration or comment')
            data.decode('utf-8', errors='strict')
        roots = {name: ET.fromstring(value) for name, value in xml.items()}
        types = roots[PARTS[0]]
        self.assertEqual(types.tag, f'{{{CT}}}Types')
        self.assertEqual([e.attrib for e in types], [
            {'Extension': 'rels', 'ContentType': 'application/vnd.openxmlformats-package.relationships+xml'},
            {'Extension': 'xml', 'ContentType': 'application/xml'},
            {'PartName': '/xl/workbook.xml', 'ContentType': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml'},
            {'PartName': '/xl/worksheets/sheet1.xml', 'ContentType': 'application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml'}])
        for name, kind, target in [(PARTS[1], 'officeDocument', 'xl/workbook.xml'),
                                   (PARTS[3], 'worksheet', 'worksheets/sheet1.xml')]:
            root = roots[name]
            self.assertEqual(root.tag, f'{{{PKG}}}Relationships')
            self.assertEqual(len(root), 1)
            self.assertEqual(root[0].tag, f'{{{PKG}}}Relationship')
            self.assertEqual(root[0].attrib, {'Id': 'rId1', 'Type': REL + '/' + kind, 'Target': target})
        workbook = roots[PARTS[2]]
        self.assertEqual(workbook.tag, f'{{{NS}}}workbook')
        self.assertEqual([e.tag for e in workbook], [f'{{{NS}}}sheets'])
        self.assertEqual(len(workbook[0]), 1)
        self.assertEqual(workbook[0][0].attrib, {'name': 'Ports' if report['reportKind'] == 'ports' else 'Connections',
            'sheetId': '1', f'{{{REL}}}id': 'rId1'})
        worksheet = roots[PARTS[4]]
        self.assertEqual(worksheet.tag, f'{{{NS}}}worksheet')
        self.assertEqual([e.tag for e in worksheet], [f'{{{NS}}}sheetData'])
        rows = []
        for row_number, row in enumerate(worksheet[0], 1):
            self.assertEqual(row.tag, f'{{{NS}}}row')
            self.assertEqual(row.attrib, {'r': str(row_number)})
            values = []
            for number, cell in enumerate(row, 1):
                letters = ''
                while number:
                    number, rest = divmod(number - 1, 26)
                    letters = chr(65 + rest) + letters
                self.assertEqual(cell.tag, f'{{{NS}}}c')
                self.assertEqual(cell.attrib, {'r': letters + str(row_number), 't': 'inlineStr'})
                self.assertEqual([e.tag for e in cell], [f'{{{NS}}}is'])
                self.assertEqual([e.tag for e in cell[0]], [f'{{{NS}}}t'])
                text = cell[0][0]
                self.assertEqual(text.attrib, {'{http://www.w3.org/XML/1998/namespace}space': 'preserve'})
                self.assertEqual(len(text), 0)
                values.append(decode_cell(text.text or ''))
            rows.append(values)
        columns = ['customer_id', 'source_revision'] + (PORT_COLUMNS if report['reportKind'] == 'ports' else
            ['connection_id', 'note', 'color', 'patch', 'cross_rack'] +
            ['from_' + c for c in PORT_COLUMNS] + ['to_' + c for c in PORT_COLUMNS])
        self.assertEqual(rows[0], columns)
        self.assertEqual(len(rows) - 1, report['rowCount'])
        self.assertLessEqual(report['rowCount'], 10000)
        for row in rows[1:]:
            self.assertEqual(len(row), len(columns))
            self.assertEqual(row[:2], [result['customerId'], str(result['revision'])])
        return [dict(zip(columns, row)) for row in rows[1:]], raw, xml

    def test_xlsx_literals_unicode_structure_and_determinism(self):
        _, _, _, rack, _, _, _, _, _, cable = self.fixture()
        forms = ['=SUM(1,2)', "'literal", '+1', '-2', '@x', ' Ñ 😃 <>&"\t\n',
                 '_x0041_ _x005F_ _x000D_ _xD83D__xDE03_ _x005F_x0041_', 'A\r\nB\rC']
        device, groups, ports = self.device('Same gn groups', rack=rack['id'],
            groups=[{'type': 'rj45', 'count': 4}, {'type': 'rj45', 'count': 4}])
        # Synthetic legacy values include CR/control/escape sequences beyond API capture policy.
        for port, value in zip(ports, forms):
            self.lab.sql(self.db, f"UPDATE inventory_port SET label={literal(value)} WHERE id='{port['id']}'")
        note = 'A\r\nB\rC\t=HYPERLINK("x") _x000A_ 😃'
        self.lab.sql(self.db, f"UPDATE inventory_connection SET note={literal(note)} WHERE id='{cable['id']}'")
        before = self.stable_inventory()
        made = self.generate()
        rows, raw, xml = self.xlsx(made)
        values = {r['port_id']: r for r in rows}
        for port, value in zip(ports, forms):
            self.assertEqual(values[port['id']]['label'], value)
        self.assertEqual(len({values[p['id']]['group_id'] for p in ports if p['gn'] == 1}), 2)
        self.assertIn(b'_x005F_x0041_', xml[PARTS[4]])
        self.assertIn(b'A_x000D_\nB_x000D_C', xml[PARTS[4]])
        self.assertEqual(self.xlsx(self.generate())[1], raw, 'Same projection produces identical workbook bytes')
        cables = self.generate(self.request('connections'))
        self.assertEqual(self.xlsx(cables)[0][0]['note'], note)
        self.assertEqual(self.stable_inventory(), before)

    def test_filters_csrf_closed_payload_and_hard_limits(self):
        _, _, _, rack, device, groups, ports, _, _, _ = self.fixture()
        self.assertEqual(self.generate(self.request(rack=rack['id']))['report']['rowCount'], 4)
        self.assertEqual(self.generate(self.request('connections', rack=rack['id']))['report']['rowCount'], 1)
        self.assertEqual(self.generate(self.request(query='CAFE\u0301', rack=rack['id']))['report']['rowCount'], 4)
        self.assertEqual(self.generate(self.request(status='reserved', family='rj45'))['report']['rowCount'], 1)
        empty = self.generate(self.request(query="' OR 1=1 --"))
        self.assertEqual(empty['report']['rowCount'], 0)
        self.assertEqual(self.xlsx(empty)[0], [])
        for payload in [{}, self.request(status='occupied'), self.request(family='rj45_poe'), self.request(query='x' * 201),
                        self.request('connections', status='free'), {**self.request(), 'limit': 10},
                        {k: v for k, v in self.request().items() if k != 'rackId'}]:
            before = self.durable()
            self.expect(self.generate(payload, status=422), 422, 'request_invalid')
            self.assertEqual(self.durable(), before)
        raw = b'{"reportKind":"ports","query":"","query":"x","status":"all","family":"all","rackId":null}'
        self.expect(self.generate(raw, status=422, headers={'Content-Type': 'application/json'}), 422, 'request_invalid')
        self.expect(self.generate(status=403, headers={'X-RackClick-CSRF': 'bad'}), 403, 'csrf_invalid')
        self.expect(self.generate(status=422, headers={'X-RackClick-Actor': ''}), 422, 'actor_invalid')
        self.expect(self.generate(status=428, headers={'If-Match': ''}), 428, 'revision_required')
        self.expect(self.generate(self.request(rack=uid()), status=404), 404, 'not_found')
        # 32767 UTF-16 units accepted; astral characters use two, not one.
        self.lab.sql(self.db, f"UPDATE inventory_port SET label=repeat(chr(128515),16383)||'A' WHERE id='{ports[0]['id']}'")
        label = next(r['label'] for r in self.xlsx(self.generate())[0] if r['port_id'] == ports[0]['id'])
        self.assertEqual(len(label.encode('utf-16-le')) // 2, 32767)
        self.lab.sql(self.db, f"UPDATE inventory_port SET label=label||'B' WHERE id='{ports[0]['id']}'")
        before = self.durable()
        self.expect(self.generate(status=422), 422, 'report_too_large')
        self.assertEqual(self.durable(), before)
        self.lab.sql(self.db, f"UPDATE inventory_port SET label='' WHERE id='{ports[0]['id']}'")
        self.lab.sql(self.db, f"INSERT INTO inventory_port(id,systemhaus_id,customer_id,device_id,group_id,type,gn,sort_order) SELECT gen_random_uuid(),'{self.house_id}','{self.customer_id}','{device['id']}','{groups[0]['id']}','rj45',g,10000+g FROM generate_series(1,10001) g")
        before = self.durable()
        self.expect(self.generate(status=422), 422, 'report_too_large')
        self.assertEqual(self.durable(), before)
        self.lab.sql(self.db, 'DELETE FROM inventory_port WHERE sort_order>=10000')
        self.lab.sql(self.db, f"INSERT INTO inventory_port(id,systemhaus_id,customer_id,device_id,group_id,type,gn,sort_order,label) SELECT gen_random_uuid(),'{self.house_id}','{self.customer_id}','{device['id']}','{groups[0]['id']}','rj45',g,10000+g,repeat('é',2000) FROM generate_series(1,1000) g")
        before = self.durable()
        self.expect(self.generate(status=422), 422, 'report_too_large')
        self.assertEqual(self.durable(), before)

    def test_permissions_isolation_format_separation_and_generic_denials(self):
        self.fixture()
        made = self.generate()
        key = made['requestId']
        reader, _, _ = self.add_user('xlsx-no-export', ['inventory.read'], self.customer_id)
        stranger, _, _ = self.add_user('xlsx-other-actor', ['inventory.read', 'reports.export'], self.customer_id)
        self.expect(self.generate(client=reader, status=403), 403, 'forbidden')
        self.expect(self.report_status(key, client=reader, status=403), 403, 'forbidden')
        self.assertEqual(self.report_status(key, client=stranger)['state'], 'notRecorded')
        foreign = self.customer('Isolated XLSX customer')['id']
        self.expect(self.generate(customer=foreign, client=stranger, status=404), 404, 'not_found')
        self.expect(self.report_status(key, customer=foreign, status=404), 404, 'not_found')
        self.expect(self.report_status(uid(), customer=foreign, client=stranger, status=404), 404, 'not_found')
        self.expect(InventoryReportsPostgres.report_status(self, key, status=404), 404, 'not_found')
        revision = self.snapshot()['revision']
        headers = {'If-Match': f'"{revision}"', 'Idempotency-Key': key, 'X-RackClick-Actor': self.admin_id}
        self.expect(self.admin.request('POST', f'/api/v1/customers/{self.customer_id}/reports/csv', self.request(), headers), 409, 'request_id_reused')
        csvkey = uid()
        csvresult = self.expect(self.admin.request('POST', f'/api/v1/customers/{self.customer_id}/reports/csv', self.request(),
            {**headers, 'Idempotency-Key': csvkey}), 200).json()
        self.assertEqual(csvresult['kind'], 'report')
        self.expect(self.report_status(csvkey, status=404), 404, 'not_found')
        self.expect(self.generate(key=csvkey, status=409), 409, 'request_id_reused')
        self.lab.sql(self.db, "DELETE FROM permission_grant WHERE capability='reports.export' AND user_group_id IN "
            f"(SELECT group_id FROM user_group_member WHERE user_id='{self.admin_id}')")
        before = self.durable()
        self.expect(self.report_status(key, status=403), 403, 'forbidden')
        self.expect(self.generate(key=key, revision=revision, status=403), 403, 'forbidden')
        path = f'/api/v1/customers/{self.customer_id}/operations/{key}'
        self.expect(self.admin.request('GET', path), 404, 'not_found')
        self.command('site.create', {'name': 'Must not create'}, key=key, status=404)
        self.expect(self.admin.request('POST', path + '/cancel', {'type': 'site.create', 'payload': {'name': 'Must not create'}}, headers), 404, 'not_found')
        hr = self.lab.sql(self.db, 'SELECT revision FROM systemhaus')
        self.expect(self.admin.request('PUT', '/api/v1/systemhaus', {'name': 'Must not rename'},
            {**headers, 'If-Match': f'"{hr}"'}), 404, 'not_found')
        state = self.expect(self.admin.request('GET', f'/api/v1/admin/users/operations/{key}'), 200).json()
        self.assertEqual(state['state'], 'notRecorded')
        self.assertIsNone(state['operation'])
        self.assertEqual(self.durable(), before)

    def test_replay_concurrency_conflict_recovery_and_restart(self):
        self.fixture()
        revision = self.snapshot()['revision']
        key = uid()
        before = self.stable_inventory()
        with ThreadPoolExecutor(2) as pool:
            results = [f.result(timeout=20) for f in [pool.submit(self.generate, key=key, revision=revision) for _ in range(2)]]
        self.assertEqual(results[0], results[1])
        self.assertEqual(self.stable_inventory(), before)
        self.assertEqual(self.lab.sql(self.db, f"SELECT count(*) FROM audit_event WHERE request_id='{key}'"), '1')
        self.command('site.create', {'name': 'Revision advances'})
        self.assertEqual(self.generate(key=key, revision=revision), results[0])
        self.expect(self.generate(revision=revision, status=412), 412, 'revision_conflict')
        self.expect(self.generate(self.request(query='different'), key=key, revision=revision, status=409), 409, 'request_id_reused')
        self.expect(self.generate(key=key, status=409), 409, 'request_id_reused')
        self.assertEqual(self.report_status(key)['operation'], results[0])
        self.assertEqual(self.report_status(uid())['state'], 'notRecorded')
        self.server.close()
        self.server = self.lab.start_server(self.db, dll=self.dll, frontend=self.frontend)
        self.admin.server = self.server
        self.assertEqual(self.report_status(key)['operation'], results[0])
        self.assertEqual(self.generate(key=key, revision=revision), results[0])

    def test_revocation_expiry_after_wait_and_before_commit(self):
        self.fixture()
        for cap, status, code in [('inventory.read', 404, 'not_found'), ('reports.export', 403, 'forbidden')]:
            reader, group, _ = self.add_user('xlsx-revoke-' + cap, ['inventory.read', 'reports.export'], self.customer_id)
            self.waiting_report(reader, lambda: self.lab.sql(self.db,
                f"DELETE FROM permission_grant WHERE user_group_id='{group}' AND capability={literal(cap)}"), status, code)
        reader, _, _ = self.add_user('xlsx-expire', ['inventory.read', 'reports.export'], self.customer_id)
        self.lab.sql(self.db, f"UPDATE app_session SET expires_at=clock_timestamp()+interval '2 seconds' WHERE user_id='{reader.actor_id}'")
        self.waiting_report(reader, lambda: None, 401, 'authentication_required', table='app_user', identity=reader.actor_id)
        self.expect(reader.login('xlsx-expire', self.password), 200)
        self.waiting_report(reader, lambda: self.lab.sql(self.db,
            f"DELETE FROM app_session WHERE user_id='{reader.actor_id}'"), 401, 'authentication_required')
        self.expect(reader.login('xlsx-expire', self.password), 200)
        self.lab.sql(self.db, "CREATE FUNCTION slow_xlsx() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.action='reports.xlsx.generate' THEN PERFORM pg_sleep(3); END IF; RETURN NEW; END $$; CREATE TRIGGER slow_xlsx BEFORE INSERT ON audit_event FOR EACH ROW EXECUTE FUNCTION slow_xlsx()")
        self.lab.sql(self.db, f"UPDATE app_session SET expires_at=clock_timestamp()+interval '2 seconds' WHERE user_id='{reader.actor_id}'")
        before = self.durable()
        self.expect(self.generate(client=reader, status=401), 401, 'authentication_required')
        self.assertEqual(self.durable(), before)

    def test_atomic_rollback_audit_metadata_and_openapi(self):
        self.fixture()
        for table in ['audit_event', 'operation']:
            predicate = "NEW.action='reports.xlsx.generate'" if table == 'audit_event' else "NEW.result_json->>'kind'='spreadsheetReport'"
            self.lab.sql(self.db, f"CREATE FUNCTION fail_xlsx() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF {predicate} THEN RAISE EXCEPTION 'synthetic XLSX rollback' USING ERRCODE='23514'; END IF; RETURN NEW; END $$; CREATE TRIGGER fail_xlsx BEFORE INSERT ON {table} FOR EACH ROW EXECUTE FUNCTION fail_xlsx()")
            before = self.durable()
            tables = self.tables()
            key = uid()
            self.expect(self.generate(key=key, status=409), 409, 'report_conflict')
            self.assertEqual(self.durable(), before)
            self.assertEqual(self.tables(), tables)
            self.assertEqual(self.report_status(key)['state'], 'notRecorded')
            self.lab.sql(self.db, f'DROP TRIGGER fail_xlsx ON {table}; DROP FUNCTION fail_xlsx()')
        revision = self.snapshot()['revision']
        made = self.generate()
        event = json.loads(self.lab.sql(self.db, f"SELECT row_to_json(a) FROM audit_event a WHERE id='{made['operationId']}'"))
        self.assertEqual(event['action'], 'reports.xlsx.generate')
        self.assertEqual(event['resource_id'], self.customer_id)
        self.assertIsNone(event['before_json'])
        self.assertEqual(event['after_json']['sourceRevision'], revision)
        self.assertEqual(event['after_json']['sha256'], made['report']['sha256'])
        self.assertNotIn('contentBase64', json.dumps(event))
        self.assertNotIn('properties', json.dumps(event))
        self.assertEqual(self.poll(revision)['events'], [])
        self.assertEqual(self.snapshot()['revision'], revision)
        document = self.expect(self.admin.request('GET', '/api/v1/openapi.json'), 200).json()
        self.assertIn('/api/v1/customers/{id}/reports/xlsx', document['paths'])
        self.assertIn('/api/v1/customers/{id}/reports/xlsx/operations/{requestId}', document['paths'])
        schemas = document['components']['schemas']
        for name in ['InventorySpreadsheetRequest', 'InventorySpreadsheetReport', 'InventorySpreadsheetResult', 'InventorySpreadsheetStatus']:
            self.assertFalse(schemas[name]['additionalProperties'])
        self.assertEqual(schemas['InventorySpreadsheetResult']['properties']['kind']['enum'], ['spreadsheetReport'])


def distribution(path):
    return {p.relative_to(path).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(path.rglob('*')) if p.is_file()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['dll', 'frontend', 'evidence']:
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--case', action='append', required=True)
    args = parser.parse_args()
    available = [n for n in InventorySpreadsheetPostgres.__dict__ if n.startswith('test_')]
    if set(args.case) - set(available):
        raise ValueError('Unknown XLSX case')
    names = [n for n in available if n in args.case]
    args.dll = args.dll.resolve()
    args.frontend = args.frontend.resolve()
    args.evidence.mkdir(parents=True, exist_ok=False)
    files = [p for p in (WORKSPACE / 'development/server/src').rglob('*.cs') if 'obj' not in p.parts and 'bin' not in p.parts]
    files += list((WORKSPACE / 'development/server/database').glob('*.sql'))
    files += [Path(__file__).resolve()] + [WORKSPACE / 'development/server/tests' / n for n in
        ['pg_support.py', 'test_postgres.py', 'test_inventory_reports.py', 'test_inventory_changes.py',
         'test_inventory_postgres.py', 'test_inventory_read_views.py', 'test_admin_grants.py']]
    def sources():
        return {p.relative_to(WORKSPACE).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    original = sources()
    server = distribution(args.dll.parent)
    frontend = distribution(args.frontend)
    report = {'utc': datetime.now(timezone.utc).isoformat(), 'platform': platform.platform(), 'python': platform.python_version(),
        'serverPath': str(args.dll.parent), 'frontendPath': str(args.frontend), 'serverHashes': server, 'frontendHashes': frontend,
        'sourceHashes': original, 'selectedCases': names, 'schemaVersion': 9, 'actualQaOpened': False,
        'excelOrLibreOfficeOpened': False}
    (args.evidence / 'inputs-before.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    lab = Lab('inventory-xlsx')
    InventorySpreadsheetPostgres.lab = lab
    report['versions'] = {name: subprocess.run([str(path), '--version'], capture_output=True, text=True,
        check=True, creationflags=NO_WINDOW).stdout.strip()
        for name, path in [('dotnet', lab.dotnet), ('postgres', lab.pg_bin / 'postgres.exe')]}
    InventorySpreadsheetPostgres.dll, InventorySpreadsheetPostgres.frontend = args.dll, args.frontend
    started = time.monotonic()
    with lab, (args.evidence / 'tests.log').open('w', encoding='utf-8') as output:
        result = unittest.TextTestRunner(stream=Tee(sys.stdout, output), verbosity=2, resultclass=EvidenceResult).run(
            unittest.TestSuite(InventorySpreadsheetPostgres(n) for n in names))
        report.update(testsRun=result.testsRun, cases=result.records, successful=result.wasSuccessful())
    report.update(elapsedSeconds=round(time.monotonic() - started, 3), labStopped=not lab.running,
        serversStopped=all(s.process.poll() is not None for s in lab.servers), sourcesUnchanged=original == sources(),
        serverUnchanged=server == distribution(args.dll.parent), frontendUnchanged=frontend == distribution(args.frontend))
    (args.evidence / 'result.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return 0 if all(report[k] for k in ['successful', 'labStopped', 'serversStopped', 'sourcesUnchanged', 'serverUnchanged', 'frontendUnchanged']) else 1


if __name__ == '__main__':
    sys.exit(main())
