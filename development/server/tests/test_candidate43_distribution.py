"""Boot the exact published43 distribution in a NEW PostgreSQL17 lab; no VM/QA."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import traceback
import uuid
from pg_support import Lab, Client, protect_directory
from test_hardware_mounting_gui import fixture
from test_hardware_batch100c import BatchSession, ordered

ROOT=Path(__file__).resolve().parents[3]
CATALOG=('hardware_definition','hardware_mount_slot','hardware_group_template','hardware_passthrough',
    'hardware_connector_template','hardware_profile_extension','hardware_group_extension')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate',type=Path,required=True)
    parser.add_argument('--expected-manifest-sha256',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();candidate=args.candidate.resolve(strict=True);out=args.output.resolve()
    assert sha(candidate/'manifest.json')==args.expected_manifest_sha256
    manifest=json.loads((candidate/'manifest.json').read_text());assert manifest['schema']==43
    for kind,files in manifest['distributions'].items():
        assert kind in ('server','frontend')
        for name,pin in files.items():
            p=(candidate/kind/name).resolve(strict=True);assert p.is_relative_to(candidate/kind) and sha(p)==pin
    assert out.is_relative_to((ROOT/'.local').resolve()) and not out.exists()
    out.mkdir(parents=True);protect_directory(out)
    lab=Lab('candidate43-published');result=dict(result='FAIL',vmAccessed=False,qaAccessed=False,
        serverSha256=sha(candidate/'server/RackClick.Server.dll'),frontendSha256=sha(candidate/'frontend/app.js'),
        windowsProviderActivated=False,serviceTokenTested=False)
    old=os.environ.get('MfaKeyStore__Enabled');os.environ['MfaKeyStore__Enabled']='false'
    try:
        with lab:
            db=lab.create_database('candidate43-published');ids,password=fixture(lab,db,candidate/'server/RackClick.Server.dll')
            assert lab.sql(db,'SELECT string_agg(version::text,\',\' ORDER BY version) FROM schema_migration')==','.join(map(str,range(1,44)))
            assert lab.sql(db,'SELECT count(*) FROM hardware_definition')=='868'
            lab.grant_runtime(db)
            for table in CATALOG:
                assert lab.sql(db,f"SELECT has_table_privilege('{db.runtime}','{table}','SELECT'),has_table_privilege('{db.runtime}','{table}','INSERT,UPDATE,DELETE,TRUNCATE')")=='t|f'
            server=lab.start_server(db,dll=candidate/'server/RackClick.Server.dll',frontend=candidate/'frontend')
            assert server.request('GET','/health/ready').status==200
            assert server.request('GET','/api/v1/me').status==401
            assert hashlib.sha256(server.request('GET','/app.js').body).hexdigest()==manifest['distributions']['frontend']['app.js']
            session=BatchSession(server,ids,password)
            assert session.client.request('GET','/api/v1/admin/users').status==200
            assert session.client.request('GET','/api/v1/me/mfa').status==200
            assert lab.sql(db,'SELECT count(*) FROM app_mfa_policy WHERE enabled')=='0'
            device=session.send(dict(profileKey='aruba-jl682a',profileVersion='aruba-20261030-v1',rackId=ids['mixedRack'],name='Candidate43 synthetic switch')).json()['result']['resourceId']
            project=ordered(session.project());assert len([p for p in project['ports'] if p['deviceId']==device])==29
            second=Client(server);assert second.login('hardware-second',password).status==200
            assert ordered(second.request('GET',session.route+'/project').json())==project
            reader=Client(server);assert reader.login('hardware-reader',password).status==200
            actor=reader.request('GET','/api/v1/me').json()['user']['id']
            denied=reader.request('POST',session.route+'/commands',{'type':'device.createHardware','payload':dict(profileKey='aruba-jl682a',profileVersion='aruba-20261030-v1',rackId=ids['mixedRack'],name='Forbidden')},
                {'X-RackClick-Actor':actor,'If-Match':f'"{session.revision}"','Idempotency-Key':str(uuid.uuid4())})
            assert denied.status==403 and ordered(session.project())==project
            server.close();server=lab.start_server(db,dll=candidate/'server/RackClick.Server.dll',frontend=candidate/'frontend')
            second=Client(server);assert second.login('hardware-second',password).status==200
            assert ordered(second.request('GET',session.route+'/project').json())==project
            result.update(result='PASS',schema=43,catalogDefinitions=868,runtimeCatalogSelectOnly=7,
                frontendServedExact=True,adminAndOwnMfaStatusRead=True,hardwareCreatedWith29Ports=True,
                readerDeniedWithoutMutation=True,secondSessionAndRestartPersistence=True,postgresql=lab.sql('postgres','SHOW server_version'))
    except BaseException as error:
        result['failureType']=type(error).__name__; (out/'failure-private.log').write_text(traceback.format_exc(),encoding='utf-8')
    finally:
        if old is None:os.environ.pop('MfaKeyStore__Enabled',None)
        else:os.environ['MfaKeyStore__Enabled']=old
        result.update(labStopped=not lab.running,serversStopped=all(s.process.poll() is not None for s in lab.servers))
        (out/'RESULTADOS.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
    return 0 if result['result']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
