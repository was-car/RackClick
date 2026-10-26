"""RC9-real adapter acceptance with ONLY freshly created synthetic fixtures."""
import argparse
from datetime import datetime, timezone
import hashlib
import http.client
import json
from pathlib import Path
import platform
import shutil
import socket
import sys
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/windows'))
from pg_support import Lab, Client, free_port, Response
from test_inventory_movement_gui import fixture
from test_postgres import EvidenceResult, Tee
from qa_schema6_source import Source4, SourceError, SOURCE_MAP, PRIVATE_FILES, artifact_manifest
from qa_schema_candidate import snapshot
from pg_lab_recovery import sha256
from qa_schema6_real_candidate import load_target, prepare, history
import qa_schema6_real_switch as coordinator

BASE4 = ROOT / '.local/candidates/grupo52-base50-7bbc812671f84aa281cf8cc926bc60b3'


class RealAdapterFixture(unittest.TestCase):
    outcomes = []
    target_schema = 6

    def setUp(self):
        self.native_dirs={}
        self.lab = Lab('manual-qa-rc9').start()
        self.db = self.lab.create_database('manual-qa-rc9')
        self.ids, self.password = fixture(self.lab, self.db, BASE4 / 'server/RackClick.Server.dll')
        self.lab.grant_runtime(self.db)
        for name in ('server', 'frontend'): shutil.copytree(BASE4 / name, self.lab.directory / name)
        self.cfg = dict(directory=str(self.lab.directory), profile='rc9', host='127.0.0.1',
            webPort=free_port(), pgPort=self.lab.port, database=self.db.name, connection=self.db.connection(self.lab.port),
            dllSha256=SOURCE_MAP['server']['RackClick.Server.dll'], bundleSha256=SOURCE_MAP['frontend']['app.js'],
            qaCustomerId=self.ids['customer'], qaCustomerName='Synthetic QA source',
            restoreSourceSha256='0'*64, restoreCounts={'customers': 2, 'racks': 2, 'devices': 3, 'ports': 6, 'connections': 1})
        self.config = self.lab.directory / 'manual-qa.json'
        self.config.write_text(json.dumps(self.cfg, indent=2), encoding='utf-8')
        origin = f'http://127.0.0.1:{self.cfg["webPort"]}'
        people = [{'role': role, 'userName': user} for role, user in [('Administrador','move-admin'),('Técnico A','move-second'),('Técnico B','move-technician'),('Lector','move-reader')]]
        values = {'QA-CUENTAS-ESTADO.json': {'ready': True, 'users': people, 'customerName': 'Synthetic QA source'},
            'qa-accounts-private.json': {'origin': origin, 'permissionsCommitted': True, 'users': [p | {'password': self.password} for p in people]},
            'RESTORE-ESTADO.json': {'restored': True, 'sourceSha256': '0'*64, 'counts': self.cfg['restoreCounts']}}
        for name, value in values.items():
            (self.lab.directory / name).write_text(json.dumps(value, indent=2), encoding='utf-8')
        (self.lab.directory / 'ACCESO-PRIVADO.txt').write_text(f'URL: {origin}\nUsuario: move-admin\nContraseña: {self.password}\n', encoding='utf-8-sig')
        (self.lab.directory / 'server.lock').write_bytes(b'0')
        home = self.lab.directory / 'switch6-home'; home.mkdir()
        self.pointer = home / 'current.json'; self.pointer.write_text(json.dumps({'directory': str(self.lab.directory)}), encoding='utf-8')
        self.source = Source4(self.lab.directory, self.pointer)
        old=self.lab.start_server(self.db,dll=self.lab.directory/'server/RackClick.Server.dll',frontend=self.lab.directory/'frontend')
        self.admin,self.reader=Client(old),Client(old)
        self.assertEqual(self.admin.login('move-admin',self.password).status,200)
        self.assertEqual(self.reader.login('move-reader',self.password).status,200)
        old.close()
        self.before = snapshot(self.source.sql)

    def tearDown(self):
        for directory,cfg in list(self.native_dirs.items()):
            if coordinator.qa_module().running(directory):coordinator.stop_application(directory,cfg)
        for directory,cfg in list(self.native_dirs.items()):
            if coordinator.pg_running(directory):coordinator.qa_module().control(directory,'stop')
        self.lab.close()
        self.outcomes.append({'sourceStopped': not self.lab.running,
                              'serversStopped': all(s.process.poll() is not None for s in self.lab.servers),
                              'nativeStopped':all(not coordinator.qa_module().running(d) and not coordinator.pg_running(d) for d in self.native_dirs)})

    def record(self,name,result):
        if result.candidate:self.native_dirs[result.candidate.lab.directory]=result.candidate.cfg

    def select(self,hook=None,**kwargs):
        self.lab.close();self.native_dirs[self.lab.directory]=self.cfg
        def combined(name,result):
            self.record(name,result)
            if hook:hook(name,result)
        try:return coordinator.switch(self.lab.directory,self.pointer,load_target(self.target_schema),hook=combined,**kwargs)
        except coordinator.RealSwitchError as error:
            if error.result:self.record('failed',error.result)
            raise

    def test_55_source4_identity_history_and_negatives(self):
        self.assertTrue(self.source.pg_running()); self.assertEqual(len(self.source.check_schema()), 4)
        self.assertEqual(self.source.artifacts(), SOURCE_MAP)
        pointer_bytes = self.pointer.read_bytes()
        self.pointer.write_text(json.dumps({'directory': str(ROOT)}), encoding='utf-8')
        try:
            with self.assertRaises(SourceError): Source4(self.lab.directory, self.pointer)
        finally: self.pointer.write_bytes(pointer_bytes)
        with self.assertRaises(SourceError): Source4(self.lab.directory, self.pointer, real=True)
        original = self.config.read_bytes(); cfg = json.loads(original); cfg['pgPort'] += 1
        self.config.write_text(json.dumps(cfg), encoding='utf-8')
        try:
            with self.assertRaises(SourceError): Source4(self.lab.directory, self.pointer)
        finally: self.config.write_bytes(original)
        dll = self.lab.directory / 'server/RackClick.Server.dll'; moved = dll.with_suffix('.missing'); dll.rename(moved)
        try:
            with self.assertRaises(SourceError): Source4(self.lab.directory, self.pointer)
        finally: moved.rename(dll)
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', self.cfg['webPort'])); listener.listen()
            with self.assertRaises(SourceError): Source4(self.lab.directory, self.pointer)
        digest = self.lab.sql(self.db, 'SELECT digest FROM schema_migration WHERE version=4')
        self.lab.sql(self.db, "UPDATE schema_migration SET digest='synthetic-invalid55' WHERE version=4")
        try:
            with self.assertRaises(SourceError): self.source.check_schema()
        finally: self.lab.sql(self.db, f"UPDATE schema_migration SET digest='{digest}' WHERE version=4")
        self.source.unchanged(); self.assertEqual(snapshot(self.source.sql), self.before)

    def test_56_new_cluster_copy_target_and_compatible4(self):
        target=load_target(self.target_schema)
        candidate=prepare(self.source,target)
        try:
            lab,db=candidate.lab,candidate.database
            self.assertNotEqual(lab.port,self.lab.port)
            self.assertEqual(snapshot(lambda q:lab.sql(candidate.recovered,q,sensitive=True)),self.before)
            self.assertEqual(history(lambda q:lab.sql(db,q,sensitive=True),lab.directory/'server',target.schema)[-1]['version'],target.schema)
            self.assertEqual([sha256(self.lab.directory/n) for n in PRIVATE_FILES],[sha256(lab.directory/n) for n in PRIVATE_FILES])
            for database,server_dir,front in [(db,lab.directory/'server',lab.directory/'frontend'),
                    (candidate.recovered,lab.directory/'versions/schema4-recovery/server',lab.directory/'versions/schema4-recovery/frontend')]:
                server=lab.start_server(database,dll=server_dir/'RackClick.Server.dll',frontend=front)
                self.assertEqual(server.request('GET','/health/ready').status,200)
                for previous in (self.admin,self.reader):
                    client=Client(server);client.cookie,client.csrf=previous.cookie,previous.csrf
                    self.assertEqual(client.request('GET','/api/v1/me').status,200)
                    self.assertEqual(client.request('GET',f'/api/v1/customers/{self.ids["customer"]}/project').status,200)
                login=Client(server);self.assertEqual(login.login('move-admin',self.password).status,200)
                server.close()
            self.assertEqual(snapshot(self.source.sql),self.before);self.source.unchanged()
        finally:
            candidate.close()
            self.outcomes.append({'sourceStopped':not candidate.lab.running,'serversStopped':all(s.process.poll() is not None for s in candidate.lab.servers),'candidateCluster':True})

    def test_57_supervisor_selection_same_url_and_persistence(self):
        result=self.select();candidate=result.candidate;directory=candidate.lab.directory;cfg=candidate.cfg
        self.assertEqual(result.state,'committed');self.assertEqual(cfg['webPort'],self.cfg['webPort'])
        self.assertEqual(json.loads(self.pointer.read_text())['directory'],str(directory))
        self.assertTrue(coordinator.qa_module().ready(directory,cfg))
        self.assertFalse(coordinator.pg_running(self.lab.directory))
        self.assertEqual(snapshot(lambda q:coordinator.read_owner(directory,cfg,q)),json.loads(candidate.journal.read_text())['candidateSnapshot'])
        admin=Client(NativeHttp(cfg));admin.cookie,admin.csrf=self.admin.cookie,self.admin.csrf
        self.assertEqual(admin.request('GET','/api/v1/me').status,200)
        fresh=Client(NativeHttp(cfg));self.assertEqual(fresh.login('move-admin',self.password).status,200)
        revision=admin.request('GET','/api/v1/systemhaus').json()['revision']
        response=admin.request('POST','/api/v1/customers',{'name':'Synthetic stable URL write'},
            {'If-Match':f'"{revision}"','Idempotency-Key':str(uuid.uuid4())})
        self.assertEqual(response.status,201);customer=response.json()['resource']['id']
        coordinator.stop_application(directory,cfg)
        process=coordinator.start_supervisor(directory,cfg)
        self.assertEqual(admin.request('GET','/api/v1/me').status,200)
        self.assertEqual(coordinator.read_owner(directory,cfg,f"SELECT count(*) FROM customer WHERE id='{customer}'"),'1')
        coordinator.stop_application(directory,cfg);process.wait(timeout=30)
        # The original remains separately recoverable and has no candidate writes.
        coordinator.qa_module().control(self.lab.directory,'start')
        try:self.assertEqual(snapshot(self.source.sql),self.before);self.source.check_schema()
        finally:coordinator.qa_module().control(self.lab.directory,'stop')


class NativeHttp:
    def __init__(self,cfg):self.port=cfg['webPort'];self.origin=f'http://127.0.0.1:{self.port}'
    def request(self,method,path,body=None,headers=None):
        headers=dict(headers or {})
        if body is not None and not isinstance(body,(str,bytes)):
            body=json.dumps(body).encode();headers.setdefault('Content-Type','application/json')
        connection=http.client.HTTPConnection('127.0.0.1',self.port,timeout=20)
        try:
            connection.request(method,path,body,headers);response=connection.getresponse()
            return Response(response.status,{k.lower():v for k,v in response.getheaders()},response.read())
        finally:connection.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--block', choices=('55','56','57','58'), required=True)
    parser.add_argument('--target-schema',type=int,choices=(6,7),default=6)
    args = parser.parse_args()
    args.evidence.mkdir(parents=True, exist_ok=False)
    inputs = [Path(__file__).resolve(), ROOT/'tools/windows/qa_schema6_source.py', ROOT/'development/server/tests/pg_support.py',
              ROOT/'development/server/tests/test_inventory_movement_gui.py',ROOT/'tools/windows/qa_schema6_real_candidate.py']
    inputs += [ROOT/'tools/windows/qa_schema6_real_switch.py',ROOT/'tools/windows/Qa-Local.py',ROOT/'tools/windows/qa_schema_switch.py',ROOT/'tools/windows/windows_job.py']
    def hashes(): return {p.relative_to(ROOT).as_posix(): sha256(p) for p in inputs}
    frozen = hashes()
    data = dict(utc=datetime.now(timezone.utc).isoformat(), platform=platform.platform(), block=args.block,
                sourceHashes=frozen, actualQaAccessed=False, sourcePair=SOURCE_MAP)
    names = [n for n in unittest.defaultTestLoader.getTestCaseNames(RealAdapterFixture) if n.startswith('test_'+args.block+'_')]
    RealAdapterFixture.target_schema=args.target_schema
    if not names: raise ValueError('Requested block is not yet implemented')
    with (args.evidence/'tests.log').open('w', encoding='utf-8') as output:
        result = unittest.TextTestRunner(stream=Tee(sys.stdout,output), verbosity=2, resultclass=EvidenceResult).run(
            unittest.TestSuite(RealAdapterFixture(n) for n in names))
    data.update(testsRun=result.testsRun,cases=result.records,successful=result.wasSuccessful(),
                labs=RealAdapterFixture.outcomes, inputsUnchanged=frozen==hashes())
    (args.evidence/'result.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    return 0 if data['successful'] and data['inputsUnchanged'] and all(v['sourceStopped'] and v['serversStopped'] and v.get('nativeStopped',True) for v in data['labs']) else 1


if __name__=='__main__': sys.exit(main())
