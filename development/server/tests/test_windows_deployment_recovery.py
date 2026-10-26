"""New Windows/PostgreSQL integration of native staging, bootstrap, backup and restore.

Only new Lab instances and copies are used. Private logs, passwords and database
archives stay under ignored .local. This is not a service/HTTPS/clean-machine test.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import secrets
import shutil
import subprocess
import sys
import time
import unittest
import uuid

from pg_support import Client, Database, Lab, NO_WINDOW, WORKSPACE, literal

ROOT = WORKSPACE
TOOLS = ROOT / 'tools/windows'
BASELINE = ROOT / 'evidence/s1-20261017/seis-tandas-180-185/CANDIDATA185.json'
BASELINE_SHA = '68aca94da20751b690af0c1c6b764a1db1004d3d63be2a12161938a3624d7706'
PS = Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_bytes())
write = lambda p, d: p.write_bytes((json.dumps(d, ensure_ascii=False, indent=2)+'\n').encode('utf-8'))


class WindowsDeploymentRecovery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.calls, cls.checkpoints = [], []
        cls.lab = None
        cls.inputs_unchanged = False
        cls.processes_stopped = False
        cls.manifest = read(BASELINE)
        assert sha(BASELINE) == BASELINE_SHA
        cls.candidate = ROOT / cls.manifest['candidateDirectory']
        sources = [Path(__file__), BASELINE, ROOT/'development/server/tests/pg_support.py']
        sources += [TOOLS/name for name in ('Test-RuntimePrerequisites.ps1', 'Test-ServerDistribution.ps1',
                    'Stage-ServerDistribution.ps1', 'Test-StagedDistribution.ps1',
                    'RackClick.Backup.ps1', 'New-RackClickDatabaseBackup.ps1', 'Restore-RackClickDatabaseBackup.ps1')]
        stage_helper = TOOLS/'RackClick.Stage.ps1'
        if stage_helper.exists(): sources.append(stage_helper)
        for kind, files in cls.manifest['distributions'].items():
            for name, digest in files.items():
                p = cls.candidate/kind/name
                assert sha(p) == digest
                sources.append(p)
        cls.guards = {p.relative_to(ROOT).as_posix(): sha(p) for p in sources}

    @classmethod
    def tearDownClass(cls):
        if cls.lab is not None:
            cls.lab.close()
            cls.processes_stopped = not cls.lab.running and all(s.process.poll() is not None for s in cls.lab.servers)
        cls.inputs_unchanged = all(sha(ROOT/n) == v for n, v in cls.guards.items())
        assert cls.inputs_unchanged and cls.processes_stopped

    def checkpoint(self, number, **details):
        self.checkpoints.append(dict(tanda=number, passed=True, **details))

    def invoke(self, name, args, expected=0):
        command = [str(PS), '-NoLogo', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                   '-File', str(TOOLS/name), *[x for k, v in args.items() for x in ('-'+k, str(v))]]
        started = time.monotonic()
        p = subprocess.run(command, capture_output=True, timeout=120, creationflags=NO_WINDOW)
        try: data = json.loads(p.stdout.decode('utf-8-sig'))
        except (ValueError, UnicodeError): data = dict(unparsed=True)
        # No raw tool output or database credentials are exported to evidence.
        self.calls.append(dict(script=name, exitCode=p.returncode, seconds=round(time.monotonic()-started,3),
                               report=data, stderrEmpty=not p.stderr))
        self.assertFalse(p.stderr, 'Native command wrote stderr; inspect private fixture')
        self.assertEqual(p.returncode, expected, data)
        self.assertEqual(data['exitCode'], expected)
        self.assertTrue(data['valid'])
        return data

    def expect(self, response, status):
        self.assertEqual(response.status, status, 'Unexpected HTTP status; response bodies remain private')
        return response

    def snapshot(self, database):
        # Hash row representations privately in memory; never export stored password/session hashes.
        names = self.lab.sql(database, "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename").splitlines()
        result = {}
        for name in names:
            self.assertRegex(name, r'^[a-z][a-z0-9_]*$')
            rows = self.lab.sql(database, f'SELECT COALESCE(jsonb_agg(row ORDER BY row::text),\'[]\'::jsonb)::text '
                                 f'FROM (SELECT to_jsonb(t) AS row FROM public.{name} t) AS source')
            result[name] = hashlib.sha256(rows.encode('utf-8')).hexdigest()
        return result

    def test_staged_bootstrap_restart_backup_and_independent_restore(self):
        self.__class__.lab = Lab('deployment-recovery188')
        lab = self.lab
        # Copy the real approved host/shared frameworks, deliberately excluding sdk.
        runtime = lab.directory/'runtime sin SDK Ω'
        runtime.mkdir()
        original = lab.dotnet.parent
        shutil.copy2(original/'dotnet.exe', runtime/'dotnet.exe')
        shutil.copytree(original/'host', runtime/'host')
        for name in ('Microsoft.NETCore.App', 'Microsoft.AspNetCore.App'):
            shutil.copytree(original/'shared'/name, runtime/'shared'/name)
        lab.dotnet = runtime/'dotnet.exe'
        sdks = subprocess.run([str(lab.dotnet), '--list-sdks'], capture_output=True, check=True, creationflags=NO_WINDOW)
        self.assertFalse(sdks.stdout.strip() or sdks.stderr.strip())
        stage = lab.directory/'distribución preparada Ω'
        staged = self.invoke('Stage-ServerDistribution.ps1', dict(
            ManifestPath=BASELINE, ExpectedManifestSha256=BASELINE_SHA,
            ServerPath=self.candidate/'server', FrontendPath=self.candidate/'frontend',
            DotNetPath=lab.dotnet, PostgresBinPath=lab.pg_bin, DestinationPath=stage))
        self.assertEqual(Path(staged['destinationPath']), stage)
        self.invoke('Test-StagedDistribution.ps1', dict(DestinationPath=stage,
                    ExpectedManifestSha256=BASELINE_SHA, ExpectedReceiptSha256=staged['receiptSha256']))
        self.checkpoint(208, sdkRequired=False, sdkListingEmpty=True, stagedFiles=36)

        lab.start()
        source = lab.create_database('source-application188')
        roles = lab.sql('postgres', f"SELECT bool_and(NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole) FROM pg_roles WHERE rolname IN ('{source.owner}','{source.runtime}')")
        self.assertEqual(roles, 't')
        self.assertNotEqual(source.owner, source.runtime)
        self.checkpoint(209, distinctOwnerRuntime=True, runtimeNoCreateDbOrRole=True)

        dll = stage/'server/RackClick.Server.dll'
        username, password = 'Admin-Ω-😀', secrets.token_urlsafe(32)
        boot = lab.bootstrap(source, username, password, dll=dll)
        (source.directory/'bootstrap-private.log').write_text(boot.stdout+boot.stderr, encoding='utf-8')
        self.assertEqual(boot.returncode, 0, 'Bootstrap failed; private fixture log retained')
        self.assertEqual(lab.sql(source, 'SELECT max(version) FROM schema_migration'), '9')
        lab.grant_runtime(source)
        self.checkpoint(210, schema=9, sourceDllSha256=sha(dll), bootstrapUnicode=True)

        server = lab.start_server(source, dll=dll, frontend=stage/'frontend')
        self.assertEqual(self.expect(server.request('GET','/'),200).body, (stage/'frontend/index.html').read_bytes())
        first, second = Client(server), Client(server)
        self.expect(first.login(username,password),200);self.expect(second.login(username,password),200)
        house = self.expect(first.request('GET','/api/v1/systemhaus'),200).json()
        request_id = str(uuid.uuid4())
        made = self.expect(first.request('POST','/api/v1/customers',{'name':'Cliente recuperación Ω 😀'},
                           {'If-Match':f'"{house["revision"]}"','Idempotency-Key':request_id}),201).json()['resource']
        listing = self.expect(second.request('GET','/api/v1/customers'),200).json()
        self.assertTrue(any(c['id']==made['id'] and c['name']==made['name'] for c in listing))
        self.assertEqual(lab.sql(source,f"SELECT count(*) FROM audit_event WHERE request_id='{request_id}'"),'1')
        self.checkpoint(211, writeCommitted=True, secondSessionRead=True, auditExactlyOne=True)

        server.close()
        restarted = lab.start_server(source,dll=dll,frontend=stage/'frontend')
        retained = Client(restarted);retained.cookie,retained.csrf=second.cookie,second.csrf
        self.expect(retained.request('GET','/api/v1/me'),200)
        listing2 = self.expect(retained.request('GET','/api/v1/customers'),200).json()
        self.assertEqual(listing2, listing)
        restarted.close()
        self.checkpoint(212, previousSessionAfterRestart=True, sameCommittedCustomers=True)

        before = self.snapshot(source)
        password_file = source.directory/'backup-password.txt'
        password_file.write_bytes((source.owner_password+'\n').encode('utf-8'))
        source_profile = source.directory/'backup-profile.json'
        write(source_profile,dict(schemaVersion=1,host='127.0.0.1',port=lab.port,database=source.name,
                                 user=source.owner,passwordFile=str(password_file)))
        backup_dir = lab.directory/'copia privada Ω'
        backup = self.invoke('New-RackClickDatabaseBackup.ps1',dict(PostgresBinPath=lab.pg_bin,
                            ProfilePath=source_profile,DestinationPath=backup_dir))
        self.assertRegex(backup['manifestSha256'],r'^[a-f0-9]{64}$')
        self.assertEqual(self.snapshot(source),before)
        self.checkpoint(213, schema9Backup=True, sourceRowsUnchanged=True, manifestSha256=backup['manifestSha256'])

        suffix = uuid.uuid4().hex[:12]
        owner, runtime_user = 'rc_recovery_owner_'+suffix, 'rc_recovery_app_'+suffix
        owner_pw, runtime_pw = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        lab.sql('postgres',f'CREATE ROLE {owner} LOGIN NOSUPERUSER CREATEDB NOCREATEROLE PASSWORD {literal(owner_pw)};'
                           f'CREATE ROLE {runtime_user} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD {literal(runtime_pw)};',sensitive=True)
        private = lab.directory/'restore-private';private.mkdir()
        restore_pw = private/'password.txt';restore_pw.write_bytes((owner_pw+'\n').encode('utf-8'))
        profile = private/'profile.json'
        write(profile,dict(schemaVersion=1,host='127.0.0.1',port=lab.port,database='postgres',user=owner,passwordFile=str(restore_pw)))
        name = 'rc_restore_'+uuid.uuid4().hex[:20]
        restored_report = self.invoke('Restore-RackClickDatabaseBackup.ps1',dict(PostgresBinPath=lab.pg_bin,
                           ProfilePath=profile,BackupPath=backup_dir,ExpectedManifestSha256=backup['manifestSha256'],NewDatabaseName=name))
        self.assertEqual(restored_report['newDatabaseName'],name)
        restored = Database(name,owner,owner_pw,runtime_user,runtime_pw,private)
        (private/'owner.pgpass').write_bytes(f'127.0.0.1:{lab.port}:{name}:{owner}:{owner_pw}\n'.encode('utf-8'))
        self.assertNotEqual(restored.name,source.name)
        self.assertEqual(self.snapshot(restored),before)
        self.checkpoint(214, independentDatabase=True, independentPgRoles=True, allPublicRowsRestored=True,
                        publicTablesCompared=len(before), snapshotSha256=hashlib.sha256(json.dumps(before,sort_keys=True).encode('utf-8')).hexdigest())

        lab.sql('postgres',f'ALTER ROLE {owner} NOCREATEDB; REVOKE ALL ON DATABASE {name} FROM PUBLIC; GRANT CONNECT ON DATABASE {name} TO {runtime_user};')
        # grant_runtime uses this private new owner's passfile; never copies old credentials.
        lab.grant_runtime(restored)
        can_create = lab.sql('postgres',f"SELECT rolcreatedb OR rolsuper OR rolcreaterole FROM pg_roles WHERE rolname='{runtime_user}'")
        self.assertEqual(can_create,'f')
        self.assertEqual(lab.sql(restored,f"SELECT has_schema_privilege('{runtime_user}','public','CREATE') OR has_database_privilege('{runtime_user}','{name}','CREATE')"),'f')
        # Restore intentionally stops before activation. Invalidate copied sessions only
        # in this new destination, after exact row comparison, before any application start.
        lab.sql(restored,'DELETE FROM app_session;')
        self.assertEqual(lab.sql(restored,'SELECT count(*) FROM app_session'),'0')
        self.checkpoint(215, runtimeGrantsExplicit=True, restoreCreatedbRevoked=True, runtimeRestricted=True, copiedSessionsRevoked=True)

        recovered = lab.start_server(restored,dll=dll,frontend=stage/'frontend')
        old_session = Client(recovered);old_session.cookie,old_session.csrf=second.cookie,second.csrf
        self.expect(old_session.request('GET','/api/v1/me'),401)
        restored_client = Client(recovered)
        self.expect(restored_client.login(username,password),200)
        self.assertEqual(self.expect(restored_client.request('GET','/api/v1/customers'),200).json(),listing)
        self.assertEqual(lab.sql(restored,f"SELECT count(*) FROM audit_event WHERE request_id='{request_id}'"),'1')
        recovered.close()
        self.assertEqual(self.snapshot(source),before)
        self.checkpoint(216, originalApplicationLogin=True, oldCookieRejected=True, auditRecovered=True, originalDatabaseUnchanged=True)
        # Full recovery of secrets, TLS, service, external files and another machine is outside scope.


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--evidence',type=Path,required=True)
    args=parser.parse_args();args.evidence.mkdir(parents=True,exist_ok=False)
    began=time.monotonic()
    with (args.evidence/'tests.log').open('w',encoding='utf-8') as out:
        result=unittest.TextTestRunner(stream=out,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(WindowsDeploymentRecovery))
    c=WindowsDeploymentRecovery
    report=dict(utc=datetime.now(timezone.utc).isoformat(),platform=platform.platform(),testsRun=result.testsRun,
                successful=result.wasSuccessful(),failures=len(result.failures),errors=len(result.errors),seconds=round(time.monotonic()-began,3),
                fixture=str(c.lab.directory) if c.lab else None,sources=getattr(c,'guards',{}),inputsUnchanged=c.inputs_unchanged,
                ownedProcessesStopped=c.processes_stopped,actualQaAccessed=False,builds=0,calls=c.calls,checkpoints=c.checkpoints,
                limits='Fresh lab, database-only restore. No installed service, HTTPS, clean Windows, other machine or adoption.')
    # Avoid persisting exception details: unittest logs contain only synthetic names/status, private diagnostics stay local.
    write(args.evidence/'result.json',report)
    print(json.dumps({k:report[k] for k in ['testsRun','successful','failures','errors','seconds','inputsUnchanged','ownedProcessesStopped']}))
    return 0 if result.wasSuccessful() and c.inputs_unchanged and c.processes_stopped else 1


if __name__=='__main__':sys.exit(main())
