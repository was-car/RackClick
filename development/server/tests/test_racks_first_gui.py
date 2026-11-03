"""Compare historical/current layout using original synthetic inventory and Edge.

Explicit binaries only. Creates its own PG17 cluster, roles, database and secrets;
never touches installed services/VM/QA. Raw output stays in a new private folder.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import secrets
import subprocess
import uuid

from pg_support import Lab, Client, NO_WINDOW, toolchain, protect_directory

ROOT = Path(__file__).resolve().parents[3]
TABLES = ['customer', 'inventory_site', 'inventory_building', 'inventory_room',
          'inventory_rack', 'inventory_device', 'inventory_port_group', 'inventory_port',
          'inventory_connection', 'inventory_connection_endpoint']


def fingerprint(lab, db):
    return {table: lab.sql(db, "SELECT md5(COALESCE(string_agg(to_jsonb(t)::text,E'\\n' ORDER BY to_jsonb(t)::text),'')) FROM " + table + ' t', sensitive=True) for table in TABLES}


def import_original(lab, db, actor, loader, plan):
    payload = dict(mode='check', connectionString=db.connection(lab.port), actorName=actor,
                   expectedHouseId=str(uuid.UUID(int=0)), expectedRevision=0, requestId=str(uuid.uuid4()))
    for mode in ['check', 'apply']:
        payload['mode'] = mode
        result = subprocess.run([str(lab.dotnet), str(loader), '--plan', str(plan)],
                                input=json.dumps(payload), text=True, encoding='utf-8', capture_output=True,
                                env=lab.environment(), timeout=120, creationflags=NO_WINDOW)
        answer = json.loads(result.stdout)
        if result.returncode or not answer.get('success'):
            raise RuntimeError('Original inventory import rejected')
        if mode == 'check':
            payload.update(expectedHouseId=answer['systemhausId'], expectedRevision=answer['expectedRevision'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dll', type=Path, required=True)
    parser.add_argument('--frontend', type=Path, required=True)
    parser.add_argument('--baseline-frontend', type=Path, required=True)
    parser.add_argument('--loader', type=Path, required=True)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--scenario', choices=['racks-first', 'report-context'], default='racks-first')
    args = parser.parse_args()
    for name in ['dll', 'frontend', 'baseline_frontend', 'loader', 'plan']:
        setattr(args, name, getattr(args, name).resolve(strict=True))
    if hashlib.sha256(args.plan.read_bytes()).hexdigest() != 'cbfe4b43a0148299f6f4c24a21dfcb5e21a8efd5ca2d08d552119ac0cd292bd7':
        raise RuntimeError('Original canonical plan required')
    args.output = args.output.absolute()
    if not args.output.resolve().is_relative_to((ROOT / '.local').resolve()):
        raise RuntimeError('Raw browser evidence must stay private under .local')
    args.output.mkdir(parents=True, exist_ok=False)
    protect_directory(args.output)
    report = dict(date=datetime.now(timezone.utc).isoformat(), result='FAIL', qaChanged=False, scenario=args.scenario,
                  serverSha256=hashlib.sha256(args.dll.read_bytes()).hexdigest(),
                  beforeAppSha256=hashlib.sha256((args.baseline_frontend / 'app.js').read_bytes()).hexdigest(),
                  afterAppSha256=hashlib.sha256((args.frontend / 'app.js').read_bytes()).hexdigest())
    try:
        with Lab('racks-first') as lab:
            db = lab.create_database('original-synthetic-layout')
            password = secrets.token_urlsafe(32)
            actor = 'layout-admin'
            boot = lab.bootstrap(db, actor, password, dll=args.dll)
            if boot.returncode:
                raise RuntimeError('Fresh bootstrap rejected')
            lab.grant_runtime(db)
            import_original(lab, db, actor, args.loader, args.plan)
            before = fingerprint(lab, db)
            customer = lab.sql(db, 'SELECT customer_id FROM inventory_device GROUP BY customer_id ORDER BY count(*) DESC LIMIT 1')
            rack = lab.sql(db, "SELECT d.rack_id FROM inventory_device d JOIN inventory_port p ON p.device_id=d.id WHERE d.customer_id='" + customer + "' AND d.rack_id IS NOT NULL AND p.type IN ('rj45','rj45_poe') AND p.status='free' AND NOT EXISTS(SELECT 1 FROM inventory_connection_endpoint e WHERE e.port_id=p.id) ORDER BY d.rack_id LIMIT 1")
            port = lab.sql(db, "SELECT p.id FROM inventory_port p JOIN inventory_device d ON d.id=p.device_id WHERE d.rack_id='" + rack + "' AND p.type IN ('rj45','rj45_poe') AND p.status='free' AND NOT EXISTS(SELECT 1 FROM inventory_connection_endpoint e WHERE e.port_id=p.id) ORDER BY p.id LIMIT 1")
            for label, frontend in [('before', args.baseline_frontend), ('after', args.frontend)]:
                server = lab.start_server(db, dll=args.dll, frontend=frontend)
                client = Client(server)
                assert client.login(actor, password).status == 200
                project = client.request('GET', '/api/v1/customers/' + customer + '/project').json()
                fixture = dict(customer=customer, rack=rack, port=port, firstRack=project['racks'][0]['id'], site=project['sites'][0]['id'],
                               otherRack=next(item['id'] for item in project['racks'] if item['id'] != rack))
                out = args.output / label
                out.mkdir()
                env = lab.environment()
                # An explicit local host, with no accidental MFA/store selection.
                env.update(MfaKeyStore__Enabled='false', RACKCLICK_TEST_ORIGIN=server.origin,
                           RACKCLICK_TEST_USERNAME=actor, RACKCLICK_TEST_PASSWORD=password,
                           RACKCLICK_TEST_OUTPUT=str(out), RACKCLICK_FIXTURE=json.dumps(fixture),
                           RACKCLICK_LAYOUT_BASELINE='1' if label == 'before' else '0')
                with (out / 'browser.log').open('wb') as log:
                    script = 'browser-racks-first.mjs' if args.scenario == 'racks-first' else 'browser-report-context.mjs'
                    result = subprocess.run([str(toolchain()['node']), str(ROOT / 'development/frontend/tests' / script)],
                                            cwd=ROOT / 'development/frontend', env=env, stdout=log, stderr=log,
                                            timeout=300, creationflags=NO_WINDOW)
                report[label + 'ExitCode'] = result.returncode
                if result.returncode:
                    raise RuntimeError(label + ' browser scenario failed')
                server.close()
            assert fingerprint(lab, db) == before
            report.update(result='PASS', inventoryTablesUnchanged=len(TABLES),
                          customers=int(lab.sql(db, 'SELECT count(*) FROM customer')),
                          ports=int(lab.sql(db, 'SELECT count(*) FROM inventory_port')))
    finally:
        (args.output / 'result.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
