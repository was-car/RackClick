"""New PG17/HTTP/Edge laboratory for two added physical media, not model coverage.

Requires explicitly frozen schema35 and36 DLLs. Never accesses an installed DB.
Raw diagnostics, generated credentials and browser profiles stay under .local.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import time
import traceback
import uuid
import xml.etree.ElementTree as ET

from pg_support import Lab, Client, NO_WINDOW, literal, protect_directory, toolchain
from test_hardware_mounting_gui import fixture
from test_hardware_catalog17 import state, migrate, runtime_sql, CATALOG
from test_hardware_batch100c import BatchSession, ordered, catalog_rows

ROOT = Path(__file__).resolve().parents[3]
TYPES = ('rj45', 'sfp', 'sfp28', 'qsfp', 'sfp56', 'qsfpdd', 'power')


def create_pair(session, rack, types):
    result = []
    for name in ('A', 'B'):
        response = session.send(dict(kind='rackEquipment', rackId=rack, sizeU=1,
            name='Synthetic connector probe '+name,
            portGroups=[dict(type=t, name=t, count=4, prefix=t+' ') for t in types]), kind='device.create')
        result.append(response.json()['result']['resourceId'])
    return result


def invariants(lab, db):
    return dict(state=state(lab, db), catalog={t:catalog_rows(lab, db, t) for t in CATALOG},
        oldPalette={t:lab.sql(db,f"SELECT COALESCE(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]') FROM {t} t")
                    for t in ('user_port_colors','user_port_color_operation')},
        migrations=lab.sql(db, 'SELECT jsonb_agg(to_jsonb(t) ORDER BY version) FROM schema_migration t'))


def upgrade(lab, old_dll, dll, out):
    db = lab.create_database('physical-media-upgrade35')
    ids, password = fixture(lab, db, old_dll)
    assert lab.sql(db, 'SELECT max(version) FROM schema_migration') == '35'
    lab.grant_runtime(db)
    server = lab.start_server(db, dll=old_dll)
    session = BatchSession(server, ids, password)
    old_types=TYPES[:4]+('power',)
    a, b = create_pair(session, ids['mixedRack'], old_types)
    project = session.project()
    for kind in old_types:
        ports = [next(p['id'] for p in project['ports'] if p['deviceId']==d and p['type']==kind) for d in (a,b)]
        session.send(dict(fromPortId=ports[0], toPortId=ports[1]), kind='connections.create')
    colors=session.client.request('GET','/api/v1/me/port-colors');assert colors.status==200
    old_colors={'rj45':'#112233','sfp':'#334455','sfp28':'#556677','qsfp':'#778899','power':'#99aabb'}
    response=session.client.request('POST','/api/v1/me/port-colors',dict(colors=old_colors),
        {'X-RackClick-Actor':session.actor,'If-Match':f'"port-colors-{colors.json()["revision"]}"','Idempotency-Key':str(uuid.uuid4())})
    assert response.status==200
    expected = ordered(session.project())
    before = invariants(lab, db)
    assert lab.sql(db, 'SELECT count(*) FROM hardware_definition') == '728'
    server.close()
    assert migrate(lab, db, dll, out/'upgrade-private.txt') == 0
    assert lab.sql(db, 'SELECT max(version) FROM schema_migration') == '36'
    after = invariants(lab, db)
    assert after['state'] == before['state'] and after['catalog'] == before['catalog'] and after['oldPalette']==before['oldPalette']
    assert lab.sql(db, 'SELECT jsonb_agg(to_jsonb(t) ORDER BY version) FROM schema_migration t WHERE version<=35') == before['migrations']
    assert migrate(lab, db, dll, out/'repeat-private.txt') == 0
    assert invariants(lab, db) == after
    lab.grant_runtime(db)
    server = lab.start_server(db, dll=dll)
    current=BatchSession(server,ids,password)
    assert ordered(current.project()) == expected
    assert current.client.request('GET','/api/v1/me/port-colors').json()['colors']==old_colors
    server.close()
    return dict(fromSchema=35, toSchema=36, preservedDefinitions=728, catalogByteEquivalent=True,
        oldFiveTypesAndFiveCablesUnchanged=True,oldPersonalPaletteAndJournalUnchanged=True,
        historicalMigrationsUnchanged=True, repeatUnchanged=True)


def fresh(lab, dll, frontend, out, browser):
    db = lab.create_database('physical-media-fresh36')
    ids, password = fixture(lab, db, dll)
    assert lab.sql(db, 'SELECT max(version) FROM schema_migration') == '36'
    lab.grant_runtime(db)
    server = lab.start_server(db, dll=dll, frontend=frontend)
    session = BatchSession(server, ids, password)
    a, b = create_pair(session, ids['mixedRack'], TYPES)
    project = session.project()
    def port(device, kind, number=1):
        return next(p for p in project['ports'] if p['deviceId']==device and p['type']==kind and p['gn']==number)
    for d in (a,b):
        assert {g['type'] for g in project['portGroups'] if g['deviceId']==d} == set(TYPES)
    # Four equivalent ordinals in distinct groups never become one port identity.
    assert len({port(a,t)['id'] for t in TYPES}) == 7
    for device,role in ((a,'inlet'),(b,'outlet')):
        chosen=port(device,'power')
        session.send(dict(deviceId=device,groupId=chosen['groupId'],groupType='power',portIds=[chosen['id']],
            changes=dict(powerRole=role)),kind='ports.update')
    replay = None
    for kind in TYPES:
        request=dict(fromPortId=port(a,kind)['id'], toPortId=port(b,kind)['id'])
        key, revision=str(uuid.uuid4()),session.revision
        response=session.send(request,kind='connections.create',key=key).json()
        if kind=='sfp56':replay=(request,key,revision,response)
    checkpoint=state(lab,db)
    assert session.send(replay[0],kind='connections.create',key=replay[1],revision=replay[2]).json()==replay[3]
    assert state(lab,db)==checkpoint
    stale=dict(fromPortId=port(a,'qsfpdd',4)['id'],toPortId=port(b,'qsfpdd',4)['id'])
    assert session.send(stale,kind='connections.create',revision=session.revision-1,status=412).json()['error']=='revision_conflict'
    assert state(lab,db)==checkpoint
    # Neither owner has a hardware profile: the new exact-type guard must still apply.
    rejected = 0
    for first in ('sfp56','qsfpdd'):
        for other in TYPES:
            if first == other:
                continue
            for left,right in ((first,other),(other,first)):
                checkpoint = state(lab, db)
                response = session.send(dict(fromPortId=port(a,left,2)['id'],toPortId=port(b,right,2)['id']),
                    kind='connections.create', status=409)
                assert response.json()['error'] == 'connection_incompatible'
                assert state(lab, db) == checkpoint
                rejected += 1
    # An explicit batch cannot borrow an equally numbered port from another group.
    selected = port(a,'sfp56',2)
    wrong = dict(deviceId=a, groupId=selected['groupId'], groupType='sfp56',
        portIds=[port(a,'qsfpdd',2)['id']], changes=dict(label='must not persist'))
    checkpoint = state(lab, db)
    assert session.send(wrong,kind='ports.update',status=422).json()['error']=='port_scope_invalid'
    assert state(lab, db)==checkpoint
    for kind in ('sfp56','qsfpdd'):
        chosen = port(a,kind,2)
        session.send(dict(deviceId=a, groupId=chosen['groupId'], groupType=kind, portIds=[chosen['id']],
            changes=dict(label='User <img> Ω '+kind, face='rear')), kind='ports.update')
    # A future/typo media value fails without creating a partial device.
    checkpoint = state(lab, db)
    response = session.send(dict(kind='rackEquipment',rackId=ids['mixedRack'],sizeU=1,name='unknown media',
        portGroups=[dict(type='qsfp-dd',name='invalid',count=1,prefix='')]),kind='device.create',status=422)
    assert response.json()['error']=='port_type_invalid' and state(lab,db)==checkpoint
    # Force an audit failure after the two new groups have been inserted.
    lab.sql(db,"CREATE FUNCTION media7_fail_audit() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic'; END $$; CREATE TRIGGER media7_fail_audit BEFORE INSERT ON audit_event FOR EACH ROW EXECUTE FUNCTION media7_fail_audit()")
    try:
        response=session.client.request('POST',session.route+'/commands',{'type':'device.create','payload':dict(kind='rackEquipment',rackId=ids['mixedRack'],sizeU=1,name='rollback',portGroups=[dict(type=t,name=t,count=1,prefix='') for t in ('sfp56','qsfpdd')])},
            {'X-RackClick-Actor':session.actor,'If-Match':f'"{session.revision}"','Idempotency-Key':str(uuid.uuid4())})
        assert response.status>=500 and state(lab,db)==checkpoint
    finally:
        lab.sql(db,'DROP TRIGGER media7_fail_audit ON audit_event; DROP FUNCTION media7_fail_audit()')
    colors=session.client.request('GET','/api/v1/me/port-colors');assert colors.status==200
    revision=colors.json()['revision']
    response=session.client.request('POST','/api/v1/me/port-colors',{'colors':{'sfp56':'#123456','qsfpdd':'#654321'}},
        {'X-RackClick-Actor':session.actor,'If-Match':f'"port-colors-{revision}"','Idempotency-Key':str(uuid.uuid4())})
    assert response.status==200
    assert session.client.request('GET','/api/v1/me/port-colors').json()['colors']=={'sfp56':'#123456','qsfpdd':'#654321'}
    assert lab.sql(db,"SELECT rackclick_user_port_colors_valid('{\"sfp56\":\"#123456\",\"qsfpdd\":\"#654321\"}'::jsonb),rackclick_user_port_colors_valid('{\"qsfp-dd\":\"#123456\"}'::jsonb)")=='t|f'
    # Real read/report consumers must retain the new family rather than fallback.
    for kind in ('sfp56','qsfpdd'):
        headers={'If-Match':f'"{session.revision}"'}
        response=session.client.request('GET',session.route+'/inventory/ports?family='+kind,headers=headers)
        assert response.status==200
        result=response.json();assert result['family']==kind and result['total']==8
        assert all(p['type']==p['family']==kind for p in result['items'])
        headers.update({'X-RackClick-Actor':session.actor,'Idempotency-Key':str(uuid.uuid4())})
        response=session.client.request('POST',session.route+'/reports/csv',dict(reportKind='ports',query='',status='all',family=kind,rackId=ids['mixedRack']),headers)
        assert response.status==200
        artifact=response.json()['report'];raw=base64.b64decode(artifact['contentBase64'])
        assert artifact['rowCount']==8 and artifact['sha256'].lower()==hashlib.sha256(raw).hexdigest()
        assert kind in raw.decode('utf-8-sig')
    headers={'If-Match':f'"{session.revision}"','X-RackClick-Actor':session.actor,'Idempotency-Key':str(uuid.uuid4())}
    response=session.client.request('POST',session.route+'/reports/rack-svg',dict(rackId=ids['mixedRack'],face='front',language='es'),headers)
    assert response.status==200
    artifact=response.json()['report'];raw=base64.b64decode(artifact['contentBase64']);xml=ET.fromstring(raw)
    assert artifact['sha256'].lower()==hashlib.sha256(raw).hexdigest()
    text={n.text for n in xml.iter() if n.tag.endswith('}text')}
    assert {'56','DD'}<=text and b'<img>' not in raw
    marked={n.attrib['data-id'] for n in xml.iter() if n.attrib.get('data-report-row')=='port'}
    assert {p['id'] for p in session.project()['ports'] if p['deviceId'] in (a,b)}<=marked
    for table in CATALOG:
        result=runtime_sql(lab,db,f"SELECT has_table_privilege(current_user,'{table}','SELECT'),has_table_privilege(current_user,'{table}','INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')")
        assert result.returncode==0 and result.stdout.strip()=='t|f'
    assert runtime_sql(lab,db,'CREATE TABLE forbidden_media7(id integer)').returncode != 0
    reader=Client(server);assert reader.login('hardware-reader',password).status==200
    actor=reader.request('GET','/api/v1/me').json()['user']['id'];checkpoint=state(lab,db)
    denied=reader.request('POST',session.route+'/commands',{'type':'connections.create','payload':dict(fromPortId=port(a,'sfp56',3)['id'],toPortId=port(b,'sfp56',3)['id'])},
        {'X-RackClick-Actor':actor,'If-Match':f'"{session.revision}"','Idempotency-Key':str(uuid.uuid4())})
    assert denied.status==403 and state(lab,db)==checkpoint
    expected=ordered(session.project())
    if browser:
        ids.update(media7=dict(a=a,b=b,types=list(TYPES)))
        env=lab.environment();env.update(RACKCLICK_TEST_ORIGIN=server.origin,RACKCLICK_TEST_USERNAME='hardware-admin',
            RACKCLICK_TEST_PASSWORD=password,RACKCLICK_TEST_OUTPUT=str(out),RACKCLICK_FIXTURE=json.dumps(ids))
        with (out/'browser-private.log').open('wb') as log:
            done=subprocess.run([str(toolchain()['node']),str(ROOT/'development/frontend/tests/browser-physical-media7.mjs')],
                cwd=ROOT/'development/frontend',env=env,stdout=log,stderr=log,timeout=300,creationflags=NO_WINDOW)
        assert done.returncode==0,'Browser test failed; log stays private'
        expected=ordered(json.loads((out/'expected-browser-project.json').read_text()))
        assert ordered(session.project())==expected
    server.close();server=lab.start_server(db,dll=dll,frontend=frontend)
    second=Client(server);assert second.login('hardware-second',password).status==200
    assert ordered(second.request('GET',session.route+'/project').json())==expected
    return dict(schema=36,newCommercialModels=0,types=list(TYPES),apiCables=7,guiCables=2 if browser else 0,
        newFamilyCrossRejections=rejected,explicitGroupIds=True,rollback=True,unknownTypeRejected=True,
        replayUnchanged=True,conflict412=True,newPersonalColorsPersisted=True,readFiltersAndCsv8RowsPerNewType=True,
        rackSvgHasDistinctLabelsAndPortIds=True,runtimeNoDdl=True,reader403=True,reloadSecondSessionAndProcessRestart=True,browserExecuted=browser)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for arg in ('dll','baseline-dll','frontend','output'):
        parser.add_argument('--'+arg,type=Path,required=True)
    parser.add_argument('--browser',action='store_true');a=parser.parse_args()
    out=a.output.resolve();assert out.is_relative_to((ROOT/'.local').resolve()) and not out.exists()
    out.mkdir(parents=True);protect_directory(out)
    report=dict(result='FAIL',qaAccessed=False,vmAccessed=False,serverSha256=hashlib.sha256(a.dll.read_bytes()).hexdigest(),
        frontendSha256=hashlib.sha256((a.frontend/'app.js').read_bytes()).hexdigest())
    lab=None;start=time.monotonic()
    try:
        lab=Lab('physical-media7')
        with lab:
            report['upgrade']=upgrade(lab,a.baseline_dll,a.dll,out)
            report['fresh']=fresh(lab,a.dll,a.frontend,out,a.browser)
            report.update(result='PASS',postgresql=lab.sql('postgres','SHOW server_version'))
    except BaseException as error:
        report.update(result='FAIL',failureType=type(error).__name__)
        (out/'runner-private.log').write_text(traceback.format_exc(),encoding='utf-8')
    finally:
        report.update(elapsedSeconds=round(time.monotonic()-start,3),labStopped=lab is None or not lab.running,
            serversStopped=lab is None or all(s.process.poll() is not None for s in lab.servers))
        (out/'RESULTADOS.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(report,indent=2))
    return 0 if report['result']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
