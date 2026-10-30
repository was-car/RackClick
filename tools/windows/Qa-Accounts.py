"""Explicit local QA fixture. No global administration/inventory rights or password resets."""
import argparse
import http.client
import importlib.util
import json
import msvcrt
import os
from pathlib import Path
import secrets
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'development/server/tests'))
from pg_support import Client, Response, literal, toolchain, NO_WINDOW

MARKER = 'QA-CUENTAS-ESTADO.json'
STATE = 'qa-accounts-private.json'
BEGIN = '\n=== CUENTAS MULTIUSUARIO QA ===\n'


def save(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')
    os.replace(temporary, path)


def checked(response, status):
    if response.status != status:
        raise RuntimeError(f'QA fixture API rejected request (HTTP {response.status}); no credentials emitted')
    return response.json()


def provision(directory, server, sql, admin_name, admin_password, dedicated_customer=None):
    directory = Path(directory).resolve()
    if directory.parent != (ROOT / '.local/labs').resolve() or not directory.name.startswith(('manual-qa-', 'qa-accounts-')):
        raise RuntimeError('Refusing unrelated laboratory')
    if not server.origin.startswith('http://127.0.0.1:'):
        raise RuntimeError('Only identified local loopback QA is allowed')
    with (directory / 'qa-accounts.lock').open('a+b') as lock:
        lock.seek(0)
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        try:
            return _provision(directory, server, sql, admin_name, admin_password, dedicated_customer)
        finally:
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


def _provision(directory, server, sql, admin_name, admin_password, dedicated_customer=None):
    (directory / MARKER).unlink(missing_ok=True)
    admin = Client(server)
    checked(admin.login(admin_name, admin_password), 200)
    house = checked(admin.request('GET', '/api/v1/systemhaus'), 200)['id']
    actor = str(uuid.UUID(sql('SELECT id FROM app_user WHERE username=' + literal(admin_name))))
    if dedicated_customer is not None:
        selected = str(uuid.UUID(dedicated_customer['id']))
        actual = sql(f"SELECT name FROM customer WHERE id='{selected}' AND systemhaus_id='{house}';")
        if actual != dedicated_customer['name']:
            raise RuntimeError('Restored QA customer identity mismatch')
    state_path = directory / STATE
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding='utf-8'))
        if state['house'] != house or state['actor'] != actor or state['origin'] != server.origin:
            raise RuntimeError('Fixture identity changed; refusing to adopt or overwrite data')
        if dedicated_customer is not None and state.get('customer', {}).get('id') != selected:
            raise RuntimeError('Refusing to change the customer scope of existing QA accounts')
    else:
        suffix = uuid.uuid4().hex[:8]
        state = {'house': house, 'actor': actor, 'origin': server.origin,
                 'customerName': 'QA multiusuario ' + suffix,
                 'customerGroup': str(uuid.uuid4()), 'technicianGroup': str(uuid.uuid4()),
                 'readerGroup': str(uuid.uuid4()), 'permissionRequest': str(uuid.uuid4()),
                 'users': [{'role': role, 'userName': name + '-' + suffix,
                            'password': secrets.token_urlsafe(24)} for role, name in
                           [('Técnico A', 'qa-tecnico-a'), ('Técnico B', 'qa-tecnico-b'), ('Lector', 'qa-lector')]]}
        if dedicated_customer is not None:
            state.update(customerName=actual, customer={'id': selected}, restoredCustomer=True)
        save(state_path, state)

    def create(row, route, body):
        if 'id' in row:
            return
        if 'request' not in row:
            row.update(request=str(uuid.uuid4()), revision=checked(admin.request('GET', '/api/v1/systemhaus'), 200)['revision'])
            save(state_path, state)
        result = checked(admin.request('POST', route, body,
            {'If-Match': f'"{row["revision"]}"', 'Idempotency-Key': row['request'], 'X-RackClick-Actor': actor}), 201)
        row['id'] = str(uuid.UUID(result['resource']['id']))
        save(state_path, state)

    state.setdefault('customer', {})
    create(state['customer'], '/api/v1/customers', {'name': state['customerName']})
    for user in state['users']:
        create(user, '/api/v1/admin/users', {'username': user['userName'], 'password': user['password']})
    # UUIDs are generated and persisted before SQL. No names are used to adopt existing groups.
    h, c, cg, tg, rg, request = [str(uuid.UUID(value)) for value in
        (house, state['customer']['id'], state['customerGroup'], state['technicianGroup'], state['readerGroup'], state['permissionRequest'])]
    users = [str(uuid.UUID(user['id'])) for user in state['users']]
    grants = [(tg, 'inventory.read'), (tg, 'inventory.edit'), (rg, 'inventory.read')]
    if not state.get('permissionsCommitted'):
        inserts = [f"INSERT INTO user_group VALUES('{tg}','{h}','QA technicians');",
                   f"INSERT INTO user_group VALUES('{rg}','{h}','QA readers');",
                   f"INSERT INTO customer_group VALUES('{cg}','{h}','QA dedicated customers');",
                   f"INSERT INTO customer_group_member VALUES('{h}','{cg}','{c}');"]
        for i, user in enumerate(users):
            inserts.append(f"INSERT INTO user_group_member VALUES('{h}','{user}','{tg if i < 2 else rg}');")
        for group, capability in grants:
            inserts.append(f"INSERT INTO permission_grant VALUES('{uuid.uuid4()}','{h}','{group}','{capability}',NULL,'{cg}');")
        for group in (tg, rg):
            inserts.append(f"INSERT INTO permission_grant VALUES('{uuid.uuid4()}','{h}','{group}','systemhaus.read',NULL,NULL);")
        inserts.append(f"UPDATE systemhaus SET revision=revision+1 WHERE id='{h}';")
        inserts.append(f"INSERT INTO audit_event(id,systemhaus_id,actor_id,request_id,action,resource_id,after_json) VALUES"
                       f"('{uuid.uuid4()}','{h}','{actor}','{request}','qa.fixture.permissions','{c}',"
                       "'{\"scope\":\"dedicated synthetic customer\",\"technicians\":2,\"readers\":1}'::jsonb);")
        # Audit identity makes replay after a lost SQL response a no-op; INSERT conflicts abort the whole fixture.
        sql('BEGIN; SELECT revision FROM systemhaus FOR UPDATE; DO $$ BEGIN IF NOT EXISTS('
            f"SELECT 1 FROM audit_event WHERE request_id='{request}' AND action='qa.fixture.permissions') THEN "
            + ''.join(inserts) + ' END IF; END $$; COMMIT;')
        state['permissionsCommitted'] = True
        save(state_path, state)
    # Verify actual login and server-side authorization before advertising availability.
    for user in reversed(state['users']):
        client = Client(server)
        checked(client.login(user['userName'], user['password']), 200)
        visible = checked(client.request('GET', '/api/v1/customers'), 200)
        if [customer['id'] for customer in visible] != [c]:
            raise RuntimeError('Fixture scope is no longer confined to the dedicated customer')
        if client.request('GET', '/api/v1/admin/users').status != 403:
            raise RuntimeError('Fixture unexpectedly has administrative privileges')
        checked(client.request('GET', '/api/v1/systemhaus'), 200)
        permissions = checked(client.request('GET', '/api/v1/me'), 200)['permissions']
        expected = {'inventory.read', 'systemhaus.read'}
        if user['role'] != 'Lector':
            expected.add('inventory.edit')
        if permissions['systemhausCapabilities'] != ['systemhaus.read'] or len(permissions['customers']) != 1 or set(permissions['customers'][0]['capabilities']) != expected:
            raise RuntimeError('Fixture effective permissions changed; refusing to advertise accounts')
    report = {'ready': True, 'customerName': state['customerName'],
              'users': [{'role': 'Administrador', 'userName': admin_name}] +
                       [{'role': user['role'], 'userName': user['userName']} for user in state['users']]}
    access = directory / 'ACCESO-PRIVADO.txt'
    original = access.read_text(encoding='utf-8-sig').split(BEGIN)[0] if access.exists() else (
        f'URL: {server.origin}\nUsuario: {admin_name}\nContraseña: {admin_password}\n')
    text = original + BEGIN + f'Cliente ficticio compartido: {state["customerName"]}\n'
    text += f'Administrador: {admin_name}\nContraseña: {admin_password}\n'
    for user in state['users']:
        text += f'{user["role"]}: {user["userName"]}\nContraseña: {user["password"]}\n'
    text += ('Técnicos: lectura/edición solo del cliente ficticio. Lector: solo lectura de ese cliente.\n'
             'Use perfiles de navegador diferentes (no dos ventanas privadas del mismo perfil).\n'
             'Las pestañas del mismo perfil comparten sesión. No compartir ni capturar este archivo.\n')
    temporary = access.with_suffix('.tmp')
    temporary.write_text(text, encoding='utf-8-sig')
    os.replace(temporary, access)
    save(directory / MARKER, report)
    return report


class LoopbackServer:
    def __init__(self, port):
        self.port = int(port)
        self.origin = f'http://127.0.0.1:{self.port}'

    def request(self, method, path, body=None, headers=None):
        headers = dict(headers or {})
        if body is not None:
            body = json.dumps(body).encode('utf-8')
            headers['Content-Type'] = 'application/json'
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=20)
        try:
            conn.request(method, path, body, headers)
            response = conn.getresponse()
            return Response(response.status, {k.lower(): v for k, v in response.getheaders()}, response.read())
        finally:
            conn.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--if-needed', action='store_true', help='Reuse previously verified fixture without extra logins')
    parser.add_argument('--profile', choices=('manual', 'rc9'), default='manual')
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location('qa_local_accounts', ROOT / 'tools/windows/Qa-Local.py')
    qa = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(qa)
    qa.configure(args.profile)
    directory, cfg = qa.load()
    if not qa.ready(directory, cfg):
        raise RuntimeError('Start INICIAR-QA.cmd first; this tool never starts or restarts services')
    if args.if_needed and (directory / MARKER).exists() and (directory / STATE).exists():
        previous = json.loads((directory / MARKER).read_text(encoding='utf-8'))
        state = json.loads((directory / STATE).read_text(encoding='utf-8'))
        expected_users = [{'role': 'Administrador', 'userName': 'wascar-qa'}] + [
            {'role': u['role'], 'userName': u['userName']} for u in state['users']]
        access = (directory / 'ACCESO-PRIVADO.txt').read_text(encoding='utf-8-sig')
        if (previous.get('ready') is True and state.get('permissionsCommitted') is True and
            state['origin'] == f'http://127.0.0.1:{cfg["webPort"]}' and previous['users'] == expected_users and
            previous['customerName'] == state['customerName'] and BEGIN in access and
            all(u['userName'] in access and u['password'] in access for u in state['users']) and
            (args.profile == 'manual' or state['customer']['id'] == cfg['qaCustomerId'])):
            print('Cuentas QA preparadas anteriormente; sin nuevos logins ni cambios. Ejecute sin --if-needed para revalidar permisos.')
            return 0
    metadata = json.loads((directory / 'lab.json').read_text(encoding='utf-8'))
    if metadata['path'] != str(directory) or metadata['port'] != cfg['pgPort']:
        raise RuntimeError('Laboratory identity mismatch')
    label = 'manual-qa-rc9' if args.profile == 'rc9' else 'manual-qa-wascar'
    database = next(row for row in metadata['databases'] if row['name'] == cfg['database'] and row['label'] == label)
    access = (directory / 'ACCESO-PRIVADO.txt').read_text(encoding='utf-8-sig').split(BEGIN)[0]
    fields = dict(line.split(': ', 1) for line in access.splitlines() if ': ' in line)
    if fields.get('Usuario') != 'wascar-qa':
        raise RuntimeError('Original manual administrator identity unavailable')
    env = dict(os.environ, PGCLIENTENCODING='UTF8', PGPASSFILE=str(directory / database['name'] / 'owner.pgpass'))

    def sql(command):
        result = subprocess.run([str(toolchain()['postgresql'].parent / 'psql.exe'), '-X', '-w',
            '-v', 'ON_ERROR_STOP=1', '-h', '127.0.0.1', '-p', str(cfg['pgPort']),
            '-U', database['owner'], '-d', database['name'], '-At'], input=command, text=True,
            encoding='utf-8', capture_output=True, env=env, creationflags=NO_WINDOW, timeout=30)
        if result.returncode:
            raise RuntimeError('Private QA fixture SQL failed; no raw database output emitted')
        return result.stdout.strip()

    target = {'id': cfg['qaCustomerId'], 'name': cfg['qaCustomerName']} if args.profile == 'rc9' else None
    provision(directory, LoopbackServer(cfg['webPort']), sql, fields['Usuario'], fields['Contraseña'], dedicated_customer=target)
    print('Cuentas QA verificadas. Credenciales solo en ACCESO-PRIVADO.txt del laboratorio identificado.')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as error:
        print(f'No se prepararon las cuentas QA: {type(error).__name__}. Revise identidad y disponibilidad del laboratorio.', file=sys.stderr)
        sys.exit(1)
