"""Cliente changes60: explicit frozen DLL/frontend; only new Windows/PostgreSQL labs."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import secrets
import sys
import time
import unittest
import uuid

from pg_support import Client, Lab, WORKSPACE, literal
from test_postgres import EvidenceResult, Tee
from test_inventory_postgres import InventoryPostgres


def uid(): return str(uuid.uuid4())


class InventoryChangesPostgres(InventoryPostgres):
    dll = frontend = None

    def setUp(self):
        self.db = self.lab.create_database(self._testMethodName)
        self.password = secrets.token_urlsafe(32)
        self.server = None
        self.assertEqual(self.lab.bootstrap(self.db, 'qa-inventory-admin', self.password, dll=self.dll).returncode, 0)
        self.lab.grant_runtime(self.db)
        self.house_id = self.lab.sql(self.db, 'SELECT id FROM systemhaus')
        self.admin_id = self.lab.sql(self.db, 'SELECT id FROM app_user')
        self.server = self.lab.start_server(self.db, dll=self.dll, frontend=self.frontend)
        self.admin = Client(self.server); self.admin.actor_id = self.admin_id
        self.expect(self.admin.login('qa-inventory-admin', self.password), 200)
        self.customer_id = self.customer('Synthetic changes customer')['id']

    def poll(self, after=None, limit=None, client=None, customer=None, query=None, status=200):
        customer = customer or self.customer_id
        parts = ([] if after is None else ['afterRevision=' + str(after)]) + ([] if limit is None else ['limit=' + str(limit)])
        query = '&'.join(parts) if query is None else query
        response = self.expect((client or self.admin).request('GET', f'/api/v1/customers/{customer}/changes' + ('?' + query if query else '')), status)
        if status != 200: return response
        value = response.json()
        self.assertEqual(set(value), {'customerId', 'currentRevision', 'nextRevision', 'hasMore', 'refreshRequired', 'events'})
        self.assertEqual(value['customerId'], customer)
        self.assertEqual(response.headers.get('etag'), f'"{value["currentRevision"]}"')
        return value

    def durable(self):
        tables = self.lab.sql(self.db, "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename").splitlines()
        sql = ' UNION ALL '.join(f'SELECT md5(COALESCE(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text)::text,\'\')) FROM public."{table}" t' for table in tables)
        return hashlib.sha256(self.lab.sql(self.db, sql).encode()).hexdigest()

    def refresh(self, after):
        value = self.poll(after)
        self.assertTrue(value['refreshRequired']); self.assertFalse(value['hasMore'])
        self.assertEqual(value['events'], [])
        self.assertEqual(value['nextRevision'], value['currentRevision'])
        return value

    def metadata(self, event, before, after, action, resource):
        self.assertEqual(set(event), {'id', 'actor', 'action', 'resourceId', 'revisionBefore', 'revisionAfter', 'occurredAt', 'context'})
        self.assertEqual(event['actor'], {'id': self.admin_id, 'userNameCurrent': 'qa-inventory-admin'})
        self.assertEqual((event['revisionBefore'], event['revisionAfter'], event['action'], event['resourceId']), (before, after, action, resource))
        uuid.UUID(event['id'])

    def no_context(self):
        return {'status': 'notAvailable', 'beforePorts': [], 'afterPorts': [], 'beforeConnections': [], 'afterConnections': []}

    def test_changes_paging_revision_order_snapshot_race(self):
        start = self.snapshot()['revision']
        operations = [self.command('site.create', {'name': 'Paging ' + str(i)}).json() for i in range(5)]
        # Informational timestamps intentionally disagree with revision/commit order.
        for index, item in enumerate(operations):
            self.lab.sql(self.db, f"UPDATE audit_event SET occurred_at='2030-01-01'::timestamptz-interval '{index} days' WHERE id='{item['operationId']}'")
        cursor, ids = start, []
        for wanted in ((2, True), (2, True), (1, False)):
            page = self.poll(cursor, 2)
            self.assertEqual((len(page['events']), page['hasMore']), wanted)
            self.assertFalse(page['refreshRequired']); self.assertEqual(page['currentRevision'], 6)
            for event in page['events']:
                self.metadata(event, cursor, cursor + 1, 'inventory.site.create', operations[cursor - 1]['result']['resourceId'])
                self.assertEqual(event['context'], self.no_context()); cursor += 1; ids.append(event['id'])
            self.assertEqual(page['nextRevision'], cursor)
        self.assertEqual(ids, [v['operationId'] for v in operations])
        self.assertEqual(self.poll()['events'], [], 'Omitted cursor must not replay old history')
        # A write after the caller's project snapshot is still seen when polling from its revision.
        saved = self.snapshot()['revision']; new = self.command('site.create', {'name': 'After project snapshot'}).json()
        self.assertEqual([e['id'] for e in self.poll(saved)['events']], [new['operationId']])
        self.lab.sql(self.db, "UPDATE app_user SET username='renamed-current-actor' WHERE id=" + literal(self.admin_id))
        self.assertEqual(self.poll(saved)['events'][0]['actor'], {'id': self.admin_id, 'userNameCurrent': 'renamed-current-actor'})
        # A real HTTP writer holds the customer row before its audit insert commits.
        # The poll must wait and then see the matching revision and event together.
        self.lab.sql(self.db, """CREATE FUNCTION slow_changes60() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN PERFORM pg_sleep(2); RETURN NEW; END; $$;
            CREATE TRIGGER slow_changes60 BEFORE INSERT ON audit_event FOR EACH ROW EXECUTE FUNCTION slow_changes60();""")
        saved = self.snapshot()['revision']
        with ThreadPoolExecutor(2) as pool:
            writer = pool.submit(self.command, 'site.create', {'name': 'Snapshot coherent'}, revision=saved)
            for _ in range(60):
                if self.lab.sql(self.db, f"SELECT count(*) FROM pg_stat_activity WHERE datname='{self.db.name}' AND usename='{self.db.runtime}' AND wait_event='PgSleep'", admin=True) != '0': break
                time.sleep(.025)
            else: self.fail('HTTP writer did not reach its audit trigger')
            page = self.poll(saved); made = writer.result(timeout=15).json()
        self.assertEqual((page['currentRevision'], page['nextRevision']), (saved + 1, saved + 1))
        self.assertEqual([e['id'] for e in page['events']], [made['operationId']])
        self.lab.sql(self.db, 'DROP TRIGGER slow_changes60 ON audit_event; DROP FUNCTION slow_changes60()')

    def test_changes_gaps_duplicates_unknown_wrappers_and_bounds(self):
        made = self.command('site.create', {'name': 'Coherence'}).json(); event = made['operationId']
        original = self.lab.sql(self.db, f"SELECT row_to_json(t) FROM audit_event t WHERE id='{event}'")
        self.refresh(3)
        for query in ('afterRevision=', 'afterRevision=0', 'afterRevision=-1', 'afterRevision=9223372036854775808',
                      'afterRevision=1.0', 'afterRevision=1&afterRevision=1', 'limit=0', 'limit=101', 'limit=', 'limit=2&limit=2'):
            self.poll(query=query, status=422)
        for mutation in ("action='inventory.unknown'", "before_json=before_json-'revision'",
                         "after_json=jsonb_set(after_json,'{revision}','3')", "after_json=jsonb_set(after_json,'{customerId}','\"" + uid() + "\"')"):
            self.lab.sql(self.db, f'UPDATE audit_event SET {mutation} WHERE id=\'{event}\'')
            self.refresh(1)
            old = json.loads(original)
            self.lab.sql(self.db, f"UPDATE audit_event SET action={literal(old['action'])},before_json={literal(json.dumps(old['before_json']))}::jsonb,after_json={literal(json.dumps(old['after_json']))}::jsonb WHERE id='{event}'")
        duplicate = uid()
        self.lab.sql(self.db, f"INSERT INTO audit_event SELECT '{duplicate}',systemhaus_id,actor_id,'{uid()}',action,resource_id,before_json,after_json,occurred_at FROM audit_event WHERE id='{event}'")
        self.refresh(1); self.lab.sql(self.db, f"DELETE FROM audit_event WHERE id='{duplicate}'")
        # A noninventory customer rename advances the same revision and must force refresh, never a synthetic inventory event.
        self.expect(self.admin.request('PUT', f'/api/v1/customers/{self.customer_id}', {'name': 'Renamed customer'},
            {'If-Match': '"2"', 'Idempotency-Key': uid()}), 200)
        self.refresh(1); self.assertEqual(self.poll()['nextRevision'], 3)
        self.lab.sql(self.db, f"DELETE FROM audit_event WHERE id='{event}'")
        self.refresh(1)

    def test_changes_current_reader_scope_and_cursor_authority(self):
        hidden = self.customer('Hidden client')['id']
        reader, group, _ = self.add_user('changes-reader', ['inventory.read'], self.customer_id)
        plain, _, _ = self.add_user('changes-plain')
        self.assertEqual(self.poll(client=reader)['currentRevision'], 1)
        for customer in (hidden, uid(), str(uuid.UUID(int=0))):
            self.assertEqual(self.poll(client=reader, customer=customer, query='afterRevision=bad&limit=0', status=404).json(), {'error': 'not_found'})
        self.poll(client=plain, query='afterRevision=bad', status=404)
        self.poll(client=Client(self.server), query='afterRevision=bad', status=401)
        self.poll(client=reader, query='afterRevision=bad', status=422)
        self.lab.sql(self.db, f"DELETE FROM permission_grant WHERE user_group_id='{group}'")
        self.poll(client=reader, status=404)
        self.expect(reader.request('GET', '/api/v1/me'), 200)
        # Explicit isolated SQL fixture permits a second House only in this test database.
        foreign_house, foreign_user, foreign_group, foreign_customer = uid(), uid(), uid(), uid()
        self.lab.sql(self.db, f"""DROP INDEX one_systemhaus_per_installation;
            INSERT INTO systemhaus(id,name) VALUES('{foreign_house}','Foreign fixture');
            INSERT INTO app_user(id,systemhaus_id,username,password_hash) SELECT '{foreign_user}','{foreign_house}','foreign-feed',password_hash FROM app_user WHERE id='{self.admin_id}';
            INSERT INTO user_group VALUES('{foreign_group}','{foreign_house}','Foreign group');
            INSERT INTO user_group_member VALUES('{foreign_house}','{foreign_user}','{foreign_group}');
            INSERT INTO permission_grant VALUES('{uid()}','{foreign_house}','{foreign_group}','inventory.read',NULL,NULL);
            INSERT INTO customer(id,systemhaus_id,name) VALUES('{foreign_customer}','{foreign_house}','Foreign customer');""")
        foreign = Client(self.server); self.expect(foreign.login('foreign-feed', self.password), 200)
        self.poll(client=foreign, customer=self.customer_id, query='afterRevision=bad', status=404)
        self.poll(customer=foreign_customer, query='afterRevision=bad', status=404)
        self.assertEqual(self.poll(client=foreign, customer=foreign_customer)['currentRevision'], 1)

    def wait_poll(self, client, table, identity, change, expected):
        label = 'changes_wait_' + uuid.uuid4().hex[:10]
        with ThreadPoolExecutor(2) as pool:
            holder = pool.submit(self.lab.sql, self.db, f"SET application_name='{label}'; BEGIN; SELECT id FROM {table} WHERE id='{identity}' FOR UPDATE; SELECT pg_sleep(3); COMMIT;")
            for _ in range(60):
                if self.lab.sql(self.db, f"SELECT count(*) FROM pg_stat_activity WHERE application_name='{label}' AND wait_event='PgSleep'", admin=True) == '1': break
                time.sleep(.025)
            else: self.fail('Lock fixture failed to start')
            pending = pool.submit(client.request, 'GET', f'/api/v1/customers/{self.customer_id}/changes?afterRevision=bad')
            for _ in range(60):
                if self.lab.sql(self.db, f"SELECT count(*) FROM pg_stat_activity WHERE datname='{self.db.name}' AND usename='{self.db.runtime}' AND wait_event_type='Lock'", admin=True) != '0': break
                time.sleep(.025)
            else: self.fail('Poll did not wait for lock')
            self.assertFalse(holder.done()); change()
            self.expect(pending.result(timeout=15), expected, 'not_found' if expected == 404 else 'authentication_required')
            holder.result(timeout=10)

    def test_changes_revocation_and_expiry_after_lock_wait(self):
        reader, group, _ = self.add_user('waiting-read', ['inventory.read'], self.customer_id)
        self.wait_poll(reader, 'customer', self.customer_id,
            lambda: self.lab.sql(self.db, f"DELETE FROM permission_grant WHERE user_group_id='{group}'"), 404)
        expired, _, _ = self.add_user('waiting-expiry', ['inventory.read'], self.customer_id)
        # Set the expiry before the actor lock; middleware sees it live, helper waits and then rechecks wall-clock time.
        self.lab.sql(self.db, f"UPDATE app_session SET expires_at=clock_timestamp()+interval '2 seconds' WHERE user_id='{expired.actor_id}'")
        self.wait_poll(expired, 'app_user', expired.actor_id, lambda: None, 401)

    def test_changes_ports_connections_captured_redaction_and_openapi(self):
        _, _, _, rack = self.hierarchy()
        device, groups, ports = self.device('Historical ports', rack=rack['id'], groups=[{'type': 'rj45', 'count': 2}, {'type': 'sfp', 'count': 2}])
        peer, _, peers = self.device('Peer', rack=rack['id'])
        marker = 'synthetic-private-note-label-property'
        selected = [next(p for p in ports if p['groupId'] == g['id'] and p['gn'] == 1) for g in groups]
        def port(p): return {k: p[k] for k in ('id', 'deviceId', 'groupId', 'type', 'gn')}
        def connection(c): return {k: c[k] for k in ('id', 'fromPortId', 'toPortId')}
        for group, target in zip(groups, selected):
            before = self.snapshot()['revision']
            changes = {'label': marker, 'properties': {'private': marker}}
            if group['type'] == 'rj45': changes['poe'] = True
            self.port_changes(device, group, [target], changes)
            event = self.poll(before)['events'][0]; current = next(p for p in self.snapshot()['ports'] if p['id'] == target['id'])
            self.assertEqual(event['context'], {'status': 'captured', 'beforePorts': [port(target)], 'afterPorts': [port(current)], 'beforeConnections': [], 'afterConnections': []})
            self.assertNotIn(marker, json.dumps(event))
            if group['type'] == 'rj45': port_event, port_revision = event['id'], before
        first = next(p for p in ports if p['groupId'] == groups[0]['id']); start = self.snapshot()['revision']
        link = self.connect(first, peers[0], note=marker, properties={'private': marker})
        event = self.poll(start)['events'][0]
        self.assertEqual(event['context'], {'status': 'captured', 'beforePorts': [], 'afterPorts': [], 'beforeConnections': [], 'afterConnections': [connection(link)]})
        self.assertNotIn(marker, json.dumps(event))
        for action, payload in [('connections.update', {'connectionId': link['id'], 'note': marker, 'patch': 'tested'}),
                                ('connections.reconnect', {'connectionId': link['id'], 'keepPortId': first['id'], 'newPortId': peers[1]['id']})]:
            before = self.snapshot()['revision']; previous = next(c for c in self.snapshot()['connections'] if c['id'] == link['id'])
            self.command(action, payload); current = next(c for c in self.snapshot()['connections'] if c['id'] == link['id'])
            event = self.poll(before)['events'][0]
            self.assertEqual(event['context'], {'status': 'captured', 'beforePorts': [], 'afterPorts': [], 'beforeConnections': [connection(previous)], 'afterConnections': [connection(current)]})
            self.assertNotIn(marker, json.dumps(event))
        before = self.snapshot()['revision']; self.command('connections.disconnect', {'connectionId': link['id']})
        event = self.poll(before)['events'][0]
        self.assertEqual(event['context']['beforeConnections'], [connection(current)]); self.assertEqual(event['context']['afterConnections'], [])
        rj45 = [p for p in ports if p['groupId'] == groups[0]['id']]
        before = self.snapshot()['revision']
        self.command('connections.createBatch', {'pairs': [{'fromPortId': p['id'], 'toPortId': q['id'], 'note': marker} for p, q in zip(rj45, peers)]})
        event = self.poll(before)['events'][0]
        self.assertEqual(event['context']['status'], 'captured'); self.assertEqual(len(event['context']['afterConnections']), 2)
        self.assertNotIn(marker, json.dumps(event))
        # SQL-only boundary fixtures isolate count limits with unique, well-typed historical references.
        raw = json.loads(self.lab.sql(self.db, f"SELECT after_json->'data'->0 FROM audit_event WHERE id='{event['id']}'"))
        captured = [raw | {'id': event['resourceId'] if i == 0 else uid(), 'fromPortId': uid(), 'toPortId': uid()} for i in range(129)]
        for maximum in (128, 129):
            self.lab.sql(self.db, f"UPDATE audit_event SET after_json=jsonb_set(after_json,'{{data}}',{literal(json.dumps(captured[:maximum]))}::jsonb) WHERE id='{event['id']}'")
            context = self.poll(before)['events'][0]['context']
            self.assertEqual(context['status'], 'captured' if maximum == 128 else 'notAvailable')
            self.assertEqual(len(context['afterConnections']), 128 if maximum == 128 else 0)
        old, new = [json.loads(self.lab.sql(self.db, f"SELECT {side}_json->'data'->0 FROM audit_event WHERE id='{port_event}'")) for side in ('before', 'after')]
        ids = [uid() for _ in range(257)]
        for maximum in (256, 257):
            prior = [old | {'id': identity, 'gn': i + 1} for i, identity in enumerate(ids[:maximum])]
            after = [new | {'id': identity, 'gn': i + 1} for i, identity in enumerate(ids[:maximum])]
            self.lab.sql(self.db, f"UPDATE audit_event SET before_json=jsonb_set(before_json,'{{data}}',{literal(json.dumps(prior))}::jsonb),after_json=jsonb_set(after_json,'{{data}}',{literal(json.dumps(after))}::jsonb) WHERE id='{port_event}'")
            context = next(e['context'] for e in self.poll(port_revision)['events'] if e['id'] == port_event)
            self.assertEqual(context['status'], 'captured' if maximum == 256 else 'notAvailable')
            self.assertEqual(len(context['afterPorts']), 256 if maximum == 256 else 0)
        for bad in ({'id': str(uuid.UUID(int=0))}, {'group_id': uid()}, {'type': 'unrecognized'}, {'gn': 0}, {'customer_id': uid()}):
            self.lab.sql(self.db, f"UPDATE audit_event SET before_json=jsonb_set(before_json,'{{data}}',{literal(json.dumps([old]))}::jsonb),after_json=jsonb_set(after_json,'{{data}}',{literal(json.dumps([new | bad]))}::jsonb) WHERE id='{port_event}'")
            self.assertEqual(next(e['context'] for e in self.poll(port_revision)['events'] if e['id'] == port_event), self.no_context())
        schema = self.expect(self.admin.request('GET', '/api/v1/openapi.json'), 200).json()
        route = schema['paths']['/api/v1/customers/{id}/changes']['get']
        self.assertEqual(route['operationId'], 'readCustomerChanges')
        self.assertEqual(set(schema['components']['schemas']['InventoryChanges']['required']), {'customerId', 'currentRevision', 'nextRevision', 'hasMore', 'refreshRequired', 'events'})

    def test_changes_commit_replay_cancel_rollback_readonly_restart(self):
        self.assertEqual(self.poll(), {'customerId': self.customer_id, 'currentRevision': 1, 'nextRevision': 1,
            'hasMore': False, 'refreshRequired': False, 'events': []})
        key = uid(); body = {'name': 'Committed synthetic site'}
        made = self.command('site.create', body, revision=1, key=key).json()
        value = self.poll(1)
        self.assertEqual((value['currentRevision'], value['nextRevision'], value['hasMore'], value['refreshRequired']), (2, 2, False, False))
        self.assertEqual([e['id'] for e in value['events']], [made['operationId']])
        self.assertEqual(self.command('site.create', body, revision=1, key=key).json(), made)
        self.cancel('site.create', {'name': 'Never created'}, uid(), revision=1)
        self.assertEqual(self.poll(1), value)
        self.lab.sql(self.db, """CREATE FUNCTION fail_changes60() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN RAISE EXCEPTION 'synthetic audit failure60'; END; $$;
            CREATE TRIGGER fail_changes60 BEFORE INSERT ON audit_event FOR EACH ROW EXECUTE FUNCTION fail_changes60();""")
        retry = uid(); before = self.durable()
        self.command('site.create', {'name': 'Atomic retry'}, revision=2, key=retry, status=503)
        self.assertEqual(before, self.durable()); self.assertEqual(self.poll(2)['events'], [])
        self.lab.sql(self.db, 'DROP TRIGGER fail_changes60 ON audit_event; DROP FUNCTION fail_changes60()')
        self.command('site.create', {'name': 'Atomic retry'}, revision=2, key=retry)
        before = self.durable(); final = self.poll(1); self.assertEqual(before, self.durable(), 'GET mutated public tables')
        self.assertEqual(len(final['events']), 2)
        second = Client(self.server); self.expect(second.login('qa-inventory-admin', self.password), 200)
        self.server.close(); self.server = self.lab.start_server(self.db, dll=self.dll, frontend=self.frontend)
        self.admin.server = self.server; second.server = self.server
        self.assertEqual(self.poll(1, client=second), final)

    def test_regression_inventory_idempotency(self):
        super().test_idempotency_replay_scope_body_and_stale_revision()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll', type=Path, required=True)
    parser.add_argument('--frontend', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--case', action='append')
    args = parser.parse_args()
    names = [n for n in unittest.defaultTestLoader.getTestCaseNames(InventoryChangesPostgres)
        if n.startswith('test_changes_') or n == 'test_regression_inventory_idempotency']
    if args.case:
        if set(args.case) - set(names): raise ValueError('Unknown changes case')
        names = [n for n in names if n in args.case]
    args.evidence.mkdir(parents=True, exist_ok=False)
    args.dll = args.dll.resolve(); args.frontend = args.frontend.resolve()
    files = list((WORKSPACE/'development/server/src/RackClick.Server').glob('*.cs')) + list((WORKSPACE/'development/server/database').glob('*.sql'))
    files += [Path(__file__).resolve(), WORKSPACE/'development/server/tests/pg_support.py', WORKSPACE/'development/server/tests/test_inventory_postgres.py']
    def hashes(): return {p.relative_to(WORKSPACE).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    def distribution(path): return {p.relative_to(path).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in path.rglob('*') if p.is_file()}
    original = hashes(); dll = hashlib.sha256(args.dll.read_bytes()).hexdigest(); frontend = distribution(args.frontend)
    report = {'utc': datetime.now(timezone.utc).isoformat(), 'platform': platform.platform(), 'dllSha256': dll,
        'frontendSha256': frontend['app.js'], 'sourceHashes': original, 'selectedCases': names, 'schemaVersion': 7,
        'actualQaOpened': False, 'transport': 'Development loopback HTTP; production HTTPS not certified'}
    lab = Lab('inventory-changes60'); InventoryChangesPostgres.lab = lab
    InventoryChangesPostgres.dll, InventoryChangesPostgres.frontend = args.dll, args.frontend
    with lab, (args.evidence/'tests.log').open('w', encoding='utf-8') as output:
        result = unittest.TextTestRunner(stream=Tee(sys.stdout, output), verbosity=2, resultclass=EvidenceResult).run(
            unittest.TestSuite(InventoryChangesPostgres(name) for name in names))
        report.update(testsRun=result.testsRun, cases=result.records, successful=result.wasSuccessful())
    report.update(labStopped=not lab.running, serversStopped=all(s.process.poll() is not None for s in lab.servers),
        inputsUnchanged=original == hashes() and dll == hashlib.sha256(args.dll.read_bytes()).hexdigest(),
        immutableUnchanged=frontend == distribution(args.frontend))
    (args.evidence/'result.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    return 0 if all(report[k] for k in ('successful', 'labStopped', 'serversStopped', 'inputsUnchanged', 'immutableUnchanged')) else 1


if __name__ == '__main__': sys.exit(main())
