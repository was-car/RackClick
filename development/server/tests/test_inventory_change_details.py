"""Bounded native Windows/PostgreSQL focuses for descriptive customer notices (428-472)."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sys
import time
import unittest

from pg_support import Client, Lab, WORKSPACE, literal
from test_postgres import EvidenceResult, Tee
from test_inventory_changes import InventoryChangesPostgres, uid


ENTITY_KEYS = {'relation', 'kind', 'id', 'name', 'parentKind', 'parentId', 'deviceKind', 'rackId', 'roomId',
               'sizeU', 'positionU', 'sortOrder', 'groupType', 'prefix', 'portCount'}
DETAIL_ACTIONS = {'site.create', 'site.update', 'site.delete', 'building.create', 'building.update', 'building.delete',
    'room.create', 'room.update', 'room.delete', 'rack.create', 'rack.update', 'rack.assignRoom', 'rack.delete', 'rack.duplicate',
    'device.create', 'device.createFromCatalog', 'device.createFromPrivateTemplate', 'device.update', 'device.move',
    'device.reorder', 'device.delete', 'devices.delete', 'device.editPortGroups'}


class InventoryChangeDetailsPostgres(InventoryChangesPostgres):
    observations = []

    def details_poll(self, after=None, limit=None, client=None, customer=None, query=None, status=200):
        customer = customer or self.customer_id
        parts = ([] if after is None else ['afterRevision=' + str(after)]) + ([] if limit is None else ['limit=' + str(limit)])
        query = '&'.join(parts) if query is None else query
        response = self.expect((client or self.admin).request('GET', f'/api/v1/customers/{customer}/changes/details' + ('?' + query if query else '')), status)
        if status != 200: return response
        value = response.json()
        self.assertEqual(set(value), {'customerId', 'currentRevision', 'nextRevision', 'hasMore', 'refreshRequired', 'events'})
        self.assertEqual(response.headers['etag'], f'"{value["currentRevision"]}"')
        self.assertEqual(response.headers['cache-control'], 'no-store')
        for event in value['events']:
            self.assertEqual(set(event), {'id', 'actor', 'action', 'resourceId', 'revisionBefore', 'revisionAfter', 'occurredAt', 'context', 'details'})
            detail = event['details']; self.assertEqual(set(detail), {'status', 'beforeEntities', 'afterEntities'})
            for side in ('beforeEntities', 'afterEntities'):
                self.assertLessEqual(len(detail[side]), 512)
                for entity in detail[side]: self.assertEqual(set(entity), ENTITY_KEYS); self.assertIsNone(entity['positionU'])
            if detail['status'] == 'notAvailable': self.assertEqual(detail, self.no_details())
        return value

    def no_details(self): return {'status': 'notAvailable', 'beforeEntities': [], 'afterEntities': []}

    def act(self, action, payload, confirmed=False, **kwargs):
        if confirmed: payload = {**payload, 'confirmationToken': self.preview(action, payload)['confirmationToken']}
        revision = self.snapshot()['revision']
        made = self.command(action, payload, revision=revision, **kwargs).json()
        page = self.details_poll(revision)
        self.assertFalse(page['refreshRequired']); self.assertEqual(len(page['events']), 1)
        event = page['events'][0]; self.assertEqual(event['id'], made['operationId'])
        self.assertEqual(event['details']['status'], 'captured', action)
        self.covered.add(action)
        return event

    def test_details_01_all_23_actions_unicode_history_groups_locations(self):
        self.covered = set()
        site = self.act('site.create', {'name': 'Sitio Café 同名'})['resourceId']
        site_event = self.details_poll(1)['events'][0]
        self.act('site.update', {'id': site, 'name': 'Sitio renombrado'})
        building = self.act('building.create', {'name': 'Gebäude', 'siteId': site})['resourceId']
        self.act('building.update', {'id': building, 'name': 'Edificio nuevo'})
        room = self.act('room.create', {'name': 'Sala Uno', 'buildingId': building})['resourceId']
        self.act('room.update', {'id': room, 'name': 'Sala Dos'})
        room2 = self.create('room', {'name': 'Sala destino', 'buildingId': building}, 'rooms')['id']
        rack = self.act('rack.create', {'name': 'Rack original', 'roomId': room, 'sizeU': 42})['resourceId']
        self.act('rack.update', {'id': rack, 'name': 'Rack actualizado', 'sizeU': 48})
        assigned = self.act('rack.assignRoom', {'id': rack, 'roomId': room2})
        self.assertEqual(assigned['details']['beforeEntities'][0]['roomId'], room)
        self.assertEqual(assigned['details']['afterEntities'][0]['roomId'], room2)
        rack2 = self.create('rack', {'name': 'Rack destino', 'roomId': room, 'sizeU': 42}, 'racks')['id']
        created = self.act('device.create', {'kind': 'rackEquipment', 'rackId': rack, 'name': 'Nombre histórico <img>', 'sizeU': 1,
            'portGroups': [{'type': 'rj45_poe', 'count': 2, 'name': 'LAN', 'prefix': 'Ω'}, {'type': 'sfp', 'count': 1, 'name': 'Óptica', 'prefix': '光'}]})
        device = created['resourceId']; groups = [e for e in created['details']['afterEntities'] if e['kind'] == 'portGroup']
        self.assertEqual({g['groupType'] for g in groups}, {'rj45', 'sfp'}); self.assertEqual({g['portCount'] for g in groups}, {1, 2})
        renamed = self.act('device.update', {'id': device, 'name': '😀' * 100})
        self.assertEqual(next(e['name'] for e in renamed['details']['afterEntities'] if e['kind'] == 'device'), '😀' * 100)
        moved = self.act('device.move', {'id': device, 'rackId': rack2})
        self.assertEqual(next(e['rackId'] for e in moved['details']['beforeEntities'] if e['kind'] == 'device'), rack)
        self.assertEqual(next(e['rackId'] for e in moved['details']['afterEntities'] if e['kind'] == 'device'), rack2)
        other = self.act('device.create', {'kind': 'rackEquipment', 'rackId': rack2, 'name': 'Segundo', 'sizeU': 2})['resourceId']
        order = self.act('device.reorder', {'rackId': rack2, 'deviceIds': [other, device]})
        self.assertEqual(next(e for e in order['details']['afterEntities'] if e['id'] == device)['sortOrder'], 1)
        self.assertEqual(next(e for e in order['details']['afterEntities'] if e['kind'] == 'rack')['relation'], 'scope')
        desired = self.desired_groups(device, add=1); desired[0].update(name='Puertos nuevos', prefix='🔌' * 100)
        changed = self.act('device.editPortGroups', {'deviceId': device, 'groups': desired, 'removedPortIds': []})
        self.assertEqual(next(e for e in changed['details']['afterEntities'] if e['id'] == desired[0]['id'])['prefix'], '🔌' * 100)
        duplicate = self.act('rack.duplicate', {'id': rack2, 'name': 'Copia', 'includeConnections': False})
        self.assertTrue(all(e['relation'] == 'source' for e in duplicate['details']['beforeEntities']))
        self.assertTrue(all(e['relation'] == 'target' for e in duplicate['details']['afterEntities']))
        self.assertEqual(next(e['name'] for e in duplicate['details']['beforeEntities'] if e['kind'] == 'rack'), 'Rack destino')
        self.act('rack.delete', {'id': duplicate['resourceId']}, confirmed=True)
        endpoints = []
        for kind in ('dose', 'endDevice'):
            endpoint = self.act('device.create', {'kind': kind, 'roomId': room, 'name': kind, 'portGroups': [{'type': 'rj45', 'count': 1}]})['resourceId']
            endpoint_move = self.act('device.move', {'id': endpoint, 'roomId': room2})
            value = next(e for e in endpoint_move['details']['afterEntities'] if e['kind'] == 'device')
            self.assertEqual((value['deviceKind'], value['parentKind'], value['parentId'], value['rackId'], value['sizeU']), (kind, 'room', room2, None, None))
            endpoints.append(endpoint)
        revision = self.snapshot()['revision']
        catalog = self.expect(self.admin.request('GET', f'/api/v1/customers/{self.customer_id}/catalog?language=es', headers={'If-Match': f'"{revision}"'}), 200).json()
        preset = next(p for p in catalog['presets'] if p['key'] == 'sw24p')
        self.act('device.createFromCatalog', {'presetKey': 'sw24p', 'catalogVersion': catalog['catalogVersion'], 'catalogSha256': catalog['catalogSha256'],
            'language': 'es', 'kind': 'rackEquipment', 'rackId': rack, 'roomId': None, 'name': 'Desde catálogo', 'color': preset['color'],
            'poeBudget': None, 'notes': {'sn': '', 'model': '', 'ip': '', 'firmware': '', 'text': 'NO EXPONER'}})
        capture = self.expect(self.admin.request('POST', f'/api/v1/customers/{self.customer_id}/catalog/private-templates',
            {'type': 'capture', 'deviceId': device, 'name': 'Plantilla privada', 'sourceRevision': self.snapshot()['revision']},
            {'If-Match': '"templates-0"', 'Idempotency-Key': uid(), 'X-RackClick-Actor': self.admin_id}), 200).json()['result']
        self.act('device.createFromPrivateTemplate', {'templateId': capture['templateId'], 'definitionVersion': 1, 'definitionSha256': capture['definitionSha256'],
            'kind': 'rackEquipment', 'rackId': rack, 'roomId': None, 'name': 'Desde plantilla', 'color': '#123456', 'poeBudget': None,
            'notes': {'sn': '', 'model': '', 'ip': '', 'firmware': '', 'text': 'NO EXPONER'}})
        deleted = self.act('device.delete', {'id': device}, confirmed=True)
        self.assertEqual(next(e['name'] for e in deleted['details']['beforeEntities'] if e['kind'] == 'device'), '😀' * 100)
        self.act('devices.delete', {'deviceIds': endpoints}, confirmed=True)
        temporary_site = self.create('site', {'name': 'Temporal'}, 'sites')['id']
        temporary_building = self.create('building', {'name': 'Temporal', 'siteId': temporary_site}, 'buildings')['id']
        temporary_room = self.create('room', {'name': 'Temporal', 'buildingId': temporary_building}, 'rooms')['id']
        self.act('room.delete', {'id': temporary_room}); self.act('building.delete', {'id': temporary_building}); self.act('site.delete', {'id': temporary_site})
        self.assertEqual(self.covered, DETAIL_ACTIONS)
        # Later updates/deletions cannot rewrite recorded names, and legacy route still has exactly eight event fields.
        page = self.details_poll(1)
        self.assertEqual(next(e for e in page['events'] if e['id'] == site_event['id']), site_event)
        historical = next(e for e in page['events'] if e['id'] == created['id'])
        self.assertEqual(next(e['name'] for e in historical['details']['afterEntities'] if e['kind'] == 'device'), 'Nombre histórico <img>')
        self.assertNotIn('NO EXPONER', json.dumps(page, ensure_ascii=False))
        for event in self.poll(1)['events']: self.assertNotIn('details', event)
        schema = self.expect(self.admin.request('GET', '/api/v1/openapi.json'), 200).json()
        self.assertEqual(schema['paths']['/api/v1/customers/{id}/changes/details']['get']['operationId'], 'readCustomerChangeDetails')
        self.assertEqual(set(schema['components']['schemas']['InventoryChangedEntity']['required']), ENTITY_KEYS)

    def test_details_02_corruption_old_capture_redaction_and_512_bound(self):
        self.covered = set(); _, _, _, rack = self.hierarchy()
        event = self.act('device.create', {'kind': 'rackEquipment', 'rackId': rack['id'], 'name': 'Safe', 'sizeU': 1,
            'portGroups': [{'type': 'rj45', 'count': 2, 'name': 'LAN', 'prefix': 'P'}]})
        revision = event['revisionBefore']; identity = event['id']
        original = json.loads(self.lab.sql(self.db, f"SELECT jsonb_build_object('before',before_json,'after',after_json) FROM audit_event WHERE id='{identity}'"))
        def replace(before, after):
            self.lab.sql(self.db, f"UPDATE audit_event SET before_json={literal(json.dumps(before))}::jsonb,after_json={literal(json.dumps(after))}::jsonb WHERE id='{identity}'")
        def unavailable():
            value = self.details_poll(revision); self.assertFalse(value['refreshRequired']); self.assertEqual(value['events'][0]['details'], self.no_details())
        mutations = [lambda a: a.pop('changeDetails'), lambda a: a['changeDetails'].update(version=2),
            lambda a: a['changeDetails'].update(houseId=uid()), lambda a: a['changeDetails'].update(customerId=uid()),
            lambda a: a['changeDetails'].update(resourceId=uid()), lambda a: a['changeDetails'].update(action='inventory.site.create'),
            lambda a: a['changeDetails'].update(entities=[1]), lambda a: a['changeDetails'].update(complete=False),
            lambda a: a['changeDetails']['entities'][0].update(extra='PRIVATE-MARKER'),
            lambda a: a['changeDetails']['entities'][0].update(prefix={'secret': 'PRIVATE-MARKER'}),
            lambda a: a['changeDetails']['entities'][0].update(positionU=1),
            lambda a: a['changeDetails']['entities'][0].update(name='X' * 101),
            lambda a: a['changeDetails']['entities'].append(a['changeDetails']['entities'][0]),
            lambda a: a['changeDetails']['entities'][0].update(parentId=uid()),
            lambda a: a['changeDetails']['entities'][0].update(parentId=event['resourceId'], rackId=event['resourceId']),
            lambda a: a['changeDetails'].update(entities=[a['changeDetails']['entities'][1]])]
        for mutation in mutations:
            after = json.loads(json.dumps(original['after'])); mutation(after); replace(original['before'], after); unavailable()
        # A bounded SQL fixture tests precisely 512 complete entities (one device and 511 valid groups) and 513 overflow.
        after = json.loads(json.dumps(original['after'])); device = next(e for e in after['changeDetails']['entities'] if e['kind'] == 'device')
        group = next(e for e in after['changeDetails']['entities'] if e['kind'] == 'portGroup')
        entities = [device] + [group | {'id': uid(), 'sortOrder': i} for i in range(512)]
        for count in (512, 513):
            after['changeDetails']['entities'] = entities[:count]; replace(original['before'], after)
            detail = self.details_poll(revision)['events'][0]['details']
            self.assertEqual(detail['status'], 'captured' if count == 512 else 'notAvailable')
            self.assertEqual(len(detail['afterEntities']), 512 if count == 512 else 0)
        # Big private extensions outside the capture are not part of the DTO and cannot inflate its projection.
        after = json.loads(json.dumps(original['after'])); after['data']['private-extension'] = 'PRIVATE-MARKER' * 100000
        replace(original['before'], after)
        response = self.expect(self.admin.request('GET', f'/api/v1/customers/{self.customer_id}/changes/details?afterRevision={revision}'), 200)
        self.assertLess(len(response.body), 5000); self.assertNotIn(b'PRIVATE-MARKER', response.body)
        replace(original['before'], original['after'])
        # One existing port action keeps its context and explicitly has no entity details.
        snapshot = self.snapshot(); g = snapshot['portGroups'][0]; ports = [p for p in snapshot['ports'] if p['groupId'] == g['id']]
        before = snapshot['revision']; self.port_changes({'id': event['resourceId']}, g, ports, {'label': 'private'})
        value = self.details_poll(before)['events'][0]
        self.assertEqual(value['context']['status'], 'captured'); self.assertEqual(value['details'], self.no_details())
        # Action invariants are checked independently of syntactically valid entity fields.
        prior = json.loads(json.dumps(original['after'])); later = json.loads(json.dumps(original['after']))
        prior['revision'] = revision
        for action, mutate in (
            ('device.update', lambda e: e.update(parentId=uid(), rackId=uid())),
            ('device.update', lambda e: e.update(sortOrder=e['sortOrder'] + 1)),
            ('device.move', lambda e: e.update(deviceKind='dose', parentKind='room', parentId=self.customer_id,
                rackId=None, roomId=self.customer_id, sizeU=None))):
            before_copy = json.loads(json.dumps(prior)); after_copy = json.loads(json.dumps(later))
            for wrapper in (before_copy, after_copy): wrapper['changeDetails']['action'] = 'inventory.' + action
            mutate(after_copy['changeDetails']['entities'][0])
            replace(before_copy, after_copy)
            self.lab.sql(self.db, f"UPDATE audit_event SET action={literal('inventory.' + action)} WHERE id='{identity}'")
            self.assertEqual(self.details_poll(revision)['events'][0]['details'], self.no_details())
        replace(original['before'], original['after'])
        self.lab.sql(self.db, f"UPDATE audit_event SET action='inventory.device.create' WHERE id='{identity}'")
        # A site capture must point to this customer, even though any UUID would be syntactically valid.
        site = self.act('site.create', {'name': 'Scope-bound site'})
        site_after = json.loads(self.lab.sql(self.db, f"SELECT after_json FROM audit_event WHERE id='{site['id']}'"))
        mutated = json.loads(json.dumps(site_after)); mutated['changeDetails']['entities'][0]['parentId'] = uid()
        self.lab.sql(self.db, f"UPDATE audit_event SET after_json={literal(json.dumps(mutated))}::jsonb WHERE id='{site['id']}'")
        self.assertEqual(self.details_poll(site['revisionBefore'])['events'][0]['details'], self.no_details())
        self.lab.sql(self.db, f"UPDATE audit_event SET after_json={literal(json.dumps(site_after))}::jsonb WHERE id='{site['id']}'")

    def wait_details(self, client, table, identity, change, expected):
        label = 'details_wait_' + uid().replace('-', '')[:10]
        with ThreadPoolExecutor(2) as pool:
            holder = pool.submit(self.lab.sql, self.db, f"SET application_name='{label}'; BEGIN; SELECT id FROM {table} WHERE id='{identity}' FOR UPDATE; SELECT pg_sleep(3); COMMIT;")
            for _ in range(70):
                if self.lab.sql(self.db, f"SELECT count(*) FROM pg_stat_activity WHERE application_name='{label}' AND wait_event='PgSleep'", admin=True) == '1': break
                time.sleep(.025)
            else: self.fail('Lock fixture did not start')
            pending = pool.submit(client.request, 'GET', f'/api/v1/customers/{self.customer_id}/changes/details?afterRevision=bad')
            for _ in range(70):
                if self.lab.sql(self.db, f"SELECT count(*) FROM pg_stat_activity WHERE datname='{self.db.name}' AND usename='{self.db.runtime}' AND wait_event_type='Lock'", admin=True) != '0': break
                time.sleep(.025)
            else: self.fail('Details read did not wait')
            change(); self.expect(pending.result(timeout=15), expected); holder.result(timeout=10)

    def test_details_03_authority_isolation_revocation_expiry_after_wait(self):
        reader, group, _ = self.add_user('details-reader', ['inventory.read'], self.customer_id)
        hidden = self.customer('Hidden details')['id']; empty = Client(self.server)
        for target in (hidden, uid()): self.details_poll(client=reader, customer=target, query='afterRevision=bad&limit=0', status=404)
        self.details_poll(client=empty, query='afterRevision=bad', status=401)
        for query in ('afterRevision=bad', 'limit=101', 'afterRevision=1&afterRevision=1'):
            self.details_poll(client=reader, query=query, status=422)
        self.wait_details(reader, 'customer', self.customer_id,
            lambda: self.lab.sql(self.db, f"DELETE FROM permission_grant WHERE user_group_id='{group}'"), 404)
        expiring, _, _ = self.add_user('details-expiring', ['inventory.read'], self.customer_id)
        self.lab.sql(self.db, f"UPDATE app_session SET expires_at=clock_timestamp()+interval '2 seconds' WHERE user_id='{expiring.actor_id}'")
        self.wait_details(expiring, 'app_user', expiring.actor_id, lambda: None, 401)

    def test_details_04_atomic_replay_gaps_readonly_restart_bounded_scale(self):
        self.covered = set(); key = uid(); revision = self.snapshot()['revision']; payload = {'name': 'Committed'}
        self.command('site.create', payload, revision=revision, key=key)
        page = self.details_poll(revision)
        self.command('site.create', payload, revision=revision, key=key); self.assertEqual(self.details_poll(revision), page)
        self.lab.sql(self.db, """CREATE FUNCTION fail_details472() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN RAISE EXCEPTION 'synthetic audit failure472'; END; $$;
            CREATE TRIGGER fail_details472 BEFORE INSERT ON audit_event FOR EACH ROW EXECUTE FUNCTION fail_details472();""")
        before = self.durable(); self.command('site.create', {'name': 'Rollback capture'}, status=503)
        self.assertEqual(self.durable(), before)
        self.lab.sql(self.db, 'DROP TRIGGER fail_details472 ON audit_event; DROP FUNCTION fail_details472()')
        second = Client(self.server); self.expect(second.login('qa-inventory-admin', self.password), 200)
        self.server.close(); self.server = self.lab.start_server(self.db, dll=self.dll, frontend=self.frontend)
        self.admin.server = self.server; second.server = self.server
        self.assertEqual(self.details_poll(revision, client=second), page)
        self.lab.sql(self.db, f"DELETE FROM audit_event WHERE id='{page['events'][0]['id']}'")
        missing = self.details_poll(revision); self.assertTrue(missing['refreshRequired']); self.assertEqual(missing['events'], [])
        # Bounded actual persistence fixture: 32 devices plus 32 groups copied and audited in one real command.
        _, _, _, rack = self.hierarchy(); devices = []
        for i in range(32): devices.append(self.device('Scale ' + str(i), rack=rack['id'], groups=[{'type': 'rj45', 'count': 2}])[0])
        started = time.perf_counter(); event = self.act('rack.duplicate', {'id': rack['id'], 'name': 'Scale copy', 'includeConnections': False})
        elapsed = time.perf_counter() - started
        self.assertEqual(len(event['details']['beforeEntities']), 65); self.assertEqual(len(event['details']['afterEntities']), 65)
        fingerprint = self.durable(); start = time.perf_counter(); read = self.details_poll(event['revisionBefore']); read_elapsed = time.perf_counter() - start
        self.assertEqual(self.durable(), fingerprint)
        self.observations.append({'fixture': '32 persisted devices, 32 groups, 64 ports; rack duplicate creates same set',
            'entitiesPerSide': 65, 'commandAndReadSeconds': round(elapsed, 6), 'readSeconds': round(read_elapsed, 6),
            'responseJsonBytes': len(json.dumps(read).encode()), 'capacityCertification': False})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll', type=Path, required=True); parser.add_argument('--frontend', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True); parser.add_argument('--case', action='append')
    args = parser.parse_args(); args.dll = args.dll.resolve(); args.frontend = args.frontend.resolve()
    names = [n for n in unittest.defaultTestLoader.getTestCaseNames(InventoryChangeDetailsPostgres) if n.startswith('test_details_')]
    if args.case:
        if set(args.case) - set(names): raise ValueError('Unknown details case')
        names = [n for n in names if n in args.case]
    args.evidence.mkdir(parents=True, exist_ok=False)
    files = list((WORKSPACE / 'development/server/src/RackClick.Server').glob('*.cs')) + list((WORKSPACE / 'development/server/database').glob('*.sql'))
    files += [Path(__file__).resolve(), WORKSPACE / 'development/server/tests/pg_support.py', WORKSPACE / 'development/server/tests/test_inventory_changes.py', WORKSPACE / 'development/server/tests/test_inventory_postgres.py']
    def hashes(): return {str(p.relative_to(WORKSPACE)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    original = hashes(); dll = hashlib.sha256(args.dll.read_bytes()).hexdigest(); front = hashlib.sha256((args.frontend / 'app.js').read_bytes()).hexdigest()
    report = {'utc': datetime.now(timezone.utc).isoformat(), 'platform': platform.platform(), 'dllSha256': dll, 'frontendSha256': front,
        'sourceHashes': original, 'selectedCases': names, 'schemaVersion': 9, 'actualQaOpened': False,
        'transport': 'Development loopback HTTP; production HTTPS not certified'}
    lab = Lab('inventory-details472'); InventoryChangeDetailsPostgres.lab = lab
    InventoryChangeDetailsPostgres.dll, InventoryChangeDetailsPostgres.frontend = args.dll, args.frontend
    with lab, (args.evidence / 'tests.log').open('w', encoding='utf-8') as output:
        result = unittest.TextTestRunner(stream=Tee(sys.stdout, output), verbosity=2, resultclass=EvidenceResult).run(
            unittest.TestSuite(InventoryChangeDetailsPostgres(name) for name in names))
        report.update(testsRun=result.testsRun, cases=result.records, successful=result.wasSuccessful())
    report.update(labStopped=not lab.running, serversStopped=all(s.process.poll() is not None for s in lab.servers),
        inputsUnchanged=original == hashes() and dll == hashlib.sha256(args.dll.read_bytes()).hexdigest(),
        frontendUnchanged=front == hashlib.sha256((args.frontend / 'app.js').read_bytes()).hexdigest(), scaleObservations=InventoryChangeDetailsPostgres.observations)
    (args.evidence / 'result.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return 0 if all(report[k] for k in ('successful', 'labStopped', 'serversStopped', 'inputsUnchanged', 'frontendUnchanged')) else 1


if __name__ == '__main__': sys.exit(main())
