"""Preview62: four destructive families, explicit frozen native inputs and isolated labs."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time
import unittest
import uuid

from pg_support import Client, Lab, WORKSPACE, NO_WINDOW, literal
from test_postgres import EvidenceResult, Tee
from test_inventory_delete_batch import DeleteBatchPostgres, distribution


class PreviewSecurityPostgres(DeleteBatchPostgres):
    def fixture62(self):
        _, _, _, rack = self.hierarchy()
        device, _, ports = self.device('Synthetic preview62', rack=rack['id'])
        self.families = {
            'rack.delete': ({'id': rack['id']}, 'inventory.delete'),
            'device.delete': ({'id': device['id']}, 'inventory.delete'),
            'device.editPortGroups': ({'deviceId': device['id'], 'removedPortIds': [ports[-1]['id']],
                'groups': self.desired_groups(device['id'], removed=[ports[-1]['id']])}, 'inventory.edit'),
            'devices.delete': ({'deviceIds': [device['id']]}, 'inventory.delete')}
        return device

    def raw62(self, kind, client=None, customer=None, revision=None, actor=None):
        client = client or self.admin
        payload = self.families[kind][0] if kind in self.families else {}
        return client.request('POST', f'/api/v1/customers/{customer or self.customer_id}/commands/preview',
            {'type': kind, 'payload': payload}, {'If-Match': f'"{revision if revision is not None else self.snapshot()["revision"]}"',
            'X-RackClick-Actor': actor or client.actor_id})

    def held62(self, lock_sql, work, during=lambda: None, status=200):
        label = 'preview62_' + uuid.uuid4().hex[:10]
        with ThreadPoolExecutor(2) as pool:
            holder = pool.submit(self.lab.sql, self.db,
                f"SET application_name='{label}'; BEGIN; {lock_sql}; SELECT pg_sleep(2.5); COMMIT;")
            self.wait_sql(f"SELECT count(*) FROM pg_stat_activity WHERE application_name='{label}' AND wait_event='PgSleep'")
            pending = pool.submit(work)
            self.wait_sql(f"SELECT count(*) FROM pg_stat_activity WHERE datname='{self.db.name}' AND usename='{self.db.runtime}' AND cardinality(pg_blocking_pids(pid))>0")
            self.assertFalse(pending.done()); during()
            result = self.expect(pending.result(timeout=15), status)
            holder.result(timeout=10)
            return result

    def test_preview_authorization_scope_and_read_only(self):
        self.fixture62()
        reader, _, _ = self.add_user('reader62', ['inventory.read'], self.customer_id)
        hidden, _, _ = self.add_user('hidden62')
        editor, _, _ = self.add_user('editor62', ['inventory.read', 'inventory.edit'], self.customer_id)
        deleter, _, _ = self.add_user('deleter62', ['inventory.read', 'inventory.delete'], self.customer_id)
        durable = self.durable()
        for kind, (_, capability) in self.families.items():
            with self.subTest(kind=kind):
                self.expect(self.raw62(kind, reader), 403)
                self.expect(self.raw62(kind, hidden), 404)
                self.expect(self.raw62(kind, customer=str(uuid.uuid4())), 404)
                self.expect(self.raw62(kind, actor=reader.actor_id), 409)
                self.expect(self.raw62(kind, revision=1), 412)
                self.expect(self.raw62(kind, editor), 200 if capability == 'inventory.edit' else 403)
                self.expect(self.raw62(kind, deleter), 200 if capability == 'inventory.delete' else 403)
        self.expect(self.raw62('future.unsupported'), 422, 'preview_unsupported')
        self.expect(self.raw62('future.unsupported', hidden), 404)
        self.expect(self.raw62('future.unsupported', reader), 403)
        self.assertEqual(self.durable(), durable, 'Preview must not write audit, operations or inventory')

    def test_preview_customer_wait_rechecks_current_permissions(self):
        self.fixture62()
        for index, (kind, (_, capability)) in enumerate(self.families.items()):
            for revoked, status in ((capability, 403), ('inventory.read', 404)):
                with self.subTest(kind=kind, revoked=revoked):
                    worker, group, _ = self.add_user(f'customer62-{index}-{status}', ['inventory.read', capability], self.customer_id)
                    self.held62(f"SELECT id FROM customer WHERE id='{self.customer_id}' FOR UPDATE",
                        lambda: self.raw62(kind, worker),
                        lambda: self.lab.sql(self.db, f"DELETE FROM permission_grant WHERE user_group_id='{group}' AND capability={literal(revoked)}"), status)

    def test_preview_session_wait_revoked_expired_and_no_inverse_lock(self):
        self.fixture62()
        for index, (kind, (_, capability)) in enumerate(self.families.items()):
            for mode in ('revoked', 'expired'):
                with self.subTest(kind=kind, mode=mode):
                    worker, _, _ = self.add_user(f'session62-{index}-{mode}', ['inventory.read', capability], self.customer_id)
                    if mode == 'expired':
                        self.lab.sql(self.db, f"UPDATE app_session SET expires_at=clock_timestamp()+interval '1.7 seconds' WHERE user_id='{worker.actor_id}'")
                    # Revocation must commit before the helper locks the session. Deleting
                    # after its SHARE lock would correctly wait for the preview to finish.
                    lock = f"SELECT id FROM customer WHERE id='{self.customer_id}' FOR UPDATE" if mode == 'revoked' else f"SELECT id FROM app_user WHERE id='{worker.actor_id}' FOR UPDATE"
                    self.held62(lock, lambda: self.raw62(kind, worker),
                        (lambda: self.lab.sql(self.db, f"DELETE FROM app_session WHERE user_id='{worker.actor_id}'")) if mode == 'revoked' else lambda: None, 401)
        # The preview must wait on customer before acquiring actor locks. A writer taking
        # customer then actor can complete; the inverse order would deadlock this fixture.
        worker, _, _ = self.add_user('order62', ['inventory.read', 'inventory.delete'], self.customer_id)
        self.held62(f"SELECT id FROM customer WHERE id='{self.customer_id}' FOR UPDATE",
            lambda: self.raw62('rack.delete', worker),
            lambda: self.lab.sql(self.db, f"BEGIN; SET LOCAL lock_timeout='500ms'; SELECT id FROM app_user WHERE id='{worker.actor_id}' FOR UPDATE; COMMIT;"))

    def test_preview_revalidation_before_return(self):
        self.fixture62()
        for index, (kind, (_, capability)) in enumerate(self.families.items()):
            with self.subTest(kind=kind):
                worker, group, _ = self.add_user(f'return62-{index}', ['inventory.read', capability], self.customer_id)
                revision = self.snapshot()['revision']
                # Snapshot SELECT waits after customer and actor locks. Grants have no actor
                # lock, so this witnesses the final check rather than the post-lock check.
                self.held62('LOCK TABLE inventory_device IN ACCESS EXCLUSIVE MODE', lambda: self.raw62(kind, worker, revision=revision),
                    lambda: self.lab.sql(self.db, f"DELETE FROM permission_grant WHERE user_group_id='{group}' AND capability={literal(capability)}"), 403)

    def test_preview_stable_snapshot_writer_both_directions_and_tokens(self):
        device = self.fixture62()
        for index, (kind, (_, capability)) in enumerate(self.families.items()):
            with self.subTest(kind=kind):
                worker, _, _ = self.add_user(f'stable62-{index}', ['inventory.read', capability], self.customer_id)
                revision = self.snapshot()['revision']
                def writer():
                    return self.command('device.update', {'id': device['id'], 'name': f'Written62-{index}'}, revision=revision)
                with ThreadPoolExecutor(3) as pool:
                    label = 'stable62_' + uuid.uuid4().hex[:8]
                    holder = pool.submit(self.lab.sql, self.db, f"SET application_name='{label}'; BEGIN; SELECT id FROM app_user WHERE id='{worker.actor_id}' FOR UPDATE; SELECT pg_sleep(2.5); COMMIT;")
                    self.wait_sql(f"SELECT count(*) FROM pg_stat_activity WHERE application_name='{label}' AND wait_event='PgSleep'")
                    preview = pool.submit(self.raw62, kind, worker)
                    witness = f"SELECT count(*) FROM pg_stat_activity WHERE datname='{self.db.name}' AND usename='{self.db.runtime}' AND cardinality(pg_blocking_pids(pid))>0"
                    self.wait_sql(witness)
                    write = pool.submit(writer); self.wait_sql(witness, minimum=2)
                    value = self.expect(preview.result(timeout=15), 200).json()
                    self.assertEqual(value['revision'], revision)
                    self.assertEqual(value['impact']['deviceIds'], [] if kind == 'device.editPortGroups' else [device['id']])
                    holder.result(timeout=10); write.result(timeout=15)
                self.command(kind, {**self.families[kind][0], 'confirmationToken': value['confirmationToken']}, revision=revision, client=worker, status=412)
                # A real API writer holds customer while waiting for its actor. The
                # preview must wait on that customer, then see the committed revision.
                revision = self.snapshot()['revision']
                with ThreadPoolExecutor(3) as pool:
                    label = 'writer62_' + uuid.uuid4().hex[:8]
                    holder = pool.submit(self.lab.sql, self.db, f"SET application_name='{label}'; BEGIN; SELECT id FROM app_user WHERE id='{self.admin_id}' FOR UPDATE; SELECT pg_sleep(2.5); COMMIT;")
                    self.wait_sql(f"SELECT count(*) FROM pg_stat_activity WHERE application_name='{label}' AND wait_event='PgSleep'")
                    write = pool.submit(self.command, 'device.update', {'id': device['id'], 'name': f'Reverse API62-{index}'}, revision=revision)
                    self.wait_sql(witness)
                    pending = pool.submit(self.raw62, kind, worker, revision=revision)
                    self.wait_sql(witness, minimum=2)
                    self.assertFalse(write.done()); self.assertFalse(pending.done())
                    holder.result(timeout=10); write.result(timeout=15)
                    self.expect(pending.result(timeout=15), 412)
        # Final single-device token executes unchanged, proving format compatibility.
        kind = 'device.delete'; preview = self.preview(kind, self.families[kind][0])
        self.command(kind, {**self.families[kind][0], 'confirmationToken': preview['confirmationToken']})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll', type=Path, required=True); parser.add_argument('--frontend', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True); parser.add_argument('--case', action='append')
    args = parser.parse_args()
    names = sorted(n for n in PreviewSecurityPostgres.__dict__ if n.startswith('test_preview_'))
    if args.case:
        if set(args.case) - set(names): raise ValueError('Unknown preview case')
        names = [n for n in names if n in args.case]
    args.evidence.mkdir(parents=True, exist_ok=False)
    args.dll = args.dll.resolve(); args.frontend = args.frontend.resolve()
    files = [p for p in (WORKSPACE/'development/server/src').rglob('*.cs') if 'obj' not in p.parts and 'bin' not in p.parts]
    files += list((WORKSPACE/'development/server/database').glob('*.sql'))
    files += [Path(__file__).resolve()] + [WORKSPACE/'development/server/tests'/name for name in
        ('pg_support.py', 'test_postgres.py', 'test_inventory_postgres.py', 'test_inventory_changes.py', 'test_inventory_delete_batch.py')]
    def sources(): return {p.relative_to(WORKSPACE).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    original = sources(); server = distribution(args.dll.parent); frontend = distribution(args.frontend)
    report = {'utc': datetime.now(timezone.utc).isoformat(), 'platform': platform.platform(), 'python': platform.python_version(),
        'serverPath': str(args.dll.parent), 'frontendPath': str(args.frontend), 'serverHashes': server, 'frontendHashes': frontend,
        'sourceHashes': original, 'selectedCases': names, 'schemaVersion': 7, 'actualQaOpened': False,
        'transport': 'Development loopback HTTP; no production HTTPS certification'}
    (args.evidence/'inputs-before.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    lab = Lab('inventory-preview62'); PreviewSecurityPostgres.lab = lab
    report['versions'] = {name: subprocess.run([str(path), '--version'], capture_output=True, text=True, check=True,
        creationflags=NO_WINDOW).stdout.strip() for name, path in [('dotnet', lab.dotnet), ('postgres', lab.pg_bin/'postgres.exe')]}
    PreviewSecurityPostgres.dll, PreviewSecurityPostgres.frontend = args.dll, args.frontend
    started = time.monotonic()
    with lab, (args.evidence/'tests.log').open('w', encoding='utf-8') as output:
        result = unittest.TextTestRunner(stream=Tee(sys.stdout, output), verbosity=2, resultclass=EvidenceResult).run(
            unittest.TestSuite(PreviewSecurityPostgres(name) for name in names))
        report.update(testsRun=result.testsRun, cases=result.records, successful=result.wasSuccessful())
    report.update(elapsedSeconds=round(time.monotonic()-started, 3), labStopped=not lab.running,
        serversStopped=all(s.process.poll() is not None for s in lab.servers), sourcesUnchanged=original == sources(),
        serverUnchanged=server == distribution(args.dll.parent), frontendUnchanged=frontend == distribution(args.frontend))
    (args.evidence/'result.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    return 0 if all(report[k] for k in ('successful', 'labStopped', 'serversStopped', 'sourcesUnchanged', 'serverUnchanged', 'frontendUnchanged')) else 1


if __name__ == '__main__': sys.exit(main())
