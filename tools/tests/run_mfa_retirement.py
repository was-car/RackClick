"""Native Windows/PG17 retirement trial in a new cluster and new private fixtures only.

Never opens an installed RackClick database/service. Source must be a caller-pinned
isolated build under .local. Raw logs, DPAPI fixtures and credentials remain private.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import secrets
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'development/server/tests'))
from pg_support import Lab,Database,NO_WINDOW,literal

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-root',required=True,type=Path)
    p.add_argument('--expected-server-sha256',required=True)
    p.add_argument('--expected-tests-sha256',required=True)
    p.add_argument('--regression',action='store_true')
    a=p.parse_args();source=a.source_root.resolve(strict=True)
    if not source.is_relative_to((ROOT/'.local').resolve()):raise ValueError('isolated_source_required')
    server=source/'development/server'
    dll=server/'src/RackClick.Server/bin/Release/net10.0/RackClick.Server.dll'
    tests=server/'tests/RackClick.Quality.Tests/bin/Release/net10.0/RackClick.Quality.Tests.dll'
    if sha(dll)!=a.expected_server_sha256 or sha(tests)!=a.expected_tests_sha256:raise ValueError('maintenance_binary_pin_invalid')
    lab=Lab('f0602-retirement');original=lab.environment
    def environment():
        env=original()
        for key in list(env):
            if key.startswith(('ConnectionStrings__','MfaKeyStore__','SqlSecret__','RACKCLICK_TEST_','RACKCLICK_F0602_','CORECLR_')):env.pop(key)
        return env
    lab.environment=environment
    result=None
    try:
        lab.start();id=uuid.uuid4();suffix=id.hex
        private=lab.directory/'native-db';private.mkdir()
        db=Database('rc_db_'+suffix,'rc_owner_'+suffix,secrets.token_urlsafe(32),'rc_backup_'+suffix,secrets.token_urlsafe(32),private)
        lab.sql('postgres',f'CREATE ROLE {db.owner} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD {literal(db.owner_password)};'
                f'CREATE ROLE {db.runtime} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD {literal(db.runtime_password)};',sensitive=True)
        lab.sql('postgres',f"CREATE DATABASE {db.name} OWNER {db.owner} TEMPLATE template0 ENCODING 'UTF8';")
        passfile=private/'owner.pgpass';passfile.write_text(f'127.0.0.1:{lab.port}:*:{db.owner}:{db.owner_password}\n','utf-8')
        boot=lab.bootstrap(db,'synthetic-maintenance-admin',secrets.token_urlsafe(24),dll=dll)
        (private/'bootstrap.private.log').write_text(boot.stdout+boot.stderr,'utf-8')
        if boot.returncode:raise RuntimeError('maintenance_bootstrap_failed')
        if lab.sql(db,'SELECT count(*),max(version) FROM schema_migration')!='45|45':raise RuntimeError('schema45_required')
        fixtures=lab.directory/'fixtures';fixtures.mkdir()
        context=lab.directory/'maintenance-context.private.json'
        context.write_text(json.dumps(dict(installationId=str(id),ownerConnection=db.connection(lab.port,runtime=False),
            ownerPgpass=str(passfile),postgresBin=str(lab.pg_bin),fixtureRoot=str(fixtures)),indent=2),'utf-8')
        env=environment();env['RACKCLICK_F0602_MAINT_CONTEXT']=str(context)
        selected='FullyQualifiedName~MfaMaintenancePostgresTests'
        if a.regression:
            selected+='|FullyQualifiedName~MfaMaintenanceCommandTests|FullyQualifiedName~MfaMaintenanceAdmissionTests|FullyQualifiedName~MfaBackupCatalogTests|FullyQualifiedName~WindowsMfaMaintenanceStoreTests|FullyQualifiedName~WindowsMfaMaintenanceServiceTests|FullyQualifiedName~MfaKeyRetentionTests|FullyQualifiedName~MfaBackupInventoryCommandTests|FullyQualifiedName~MfaKeyStoreInitCommandTests|FullyQualifiedName~MfaWindowsHostCompositionTests|FullyQualifiedName~MfaWindowsHostHttpTests'
            # Existing host tests create their own temporary DBs; setup authority is confined to this new cluster.
            env['RACKCLICK_TEST_PG_ADMIN']=f'Host=127.0.0.1;Port={lab.port};Database=postgres;Username={lab.admin};Password={lab.admin_password};Pooling=false;SSL Mode=Disable'
        command=[str(lab.dotnet),'test','tests/RackClick.Quality.Tests/RackClick.Quality.Tests.csproj','-c','Release','--no-build','--no-restore',
                 '--filter',selected,'--logger','trx;LogFileName='+str(lab.directory/'maintenance.trx'),'-bl:'+str(lab.directory/'maintenance-{}.binlog')]
        with (lab.directory/'tests.private.log').open('wb') as log:
            ran=subprocess.run(command,cwd=server,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=300,creationflags=NO_WINDOW)
        trx=ET.parse(lab.directory/'maintenance.trx');counts=trx.find('.//{*}Counters').attrib
        result=dict(success=ran.returncode==0,exitCode=ran.returncode,testCounts=counts,postgresql='17.11',schema=45,
            sourceServerSha256=sha(dll),sourceTestsSha256=sha(tests),regression=a.regression,sourceIsolated=True,
            nativeDatabaseCreated=True,windowsDpapiFixtures=True,installedServicesAccessed=False,vmAccessed=False,
            productionElevatedCliPositive=False,physicalKeysDeleted=False,fixturesPreserved=True,privateLab=str(lab.directory))
    finally:lab.close()
    result['ownClusterStopped']=not lab.running
    (lab.directory/'result-sanitized.json').write_text(json.dumps(result,indent=2)+'\n','utf-8')
    print(json.dumps(result));return result['exitCode']

if __name__=='__main__':raise SystemExit(main())
