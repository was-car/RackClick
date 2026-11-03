"""Mixed-family K integration in new PostgreSQL17 databases only; no installed QA/VM."""
import argparse
from collections import Counter
import hashlib,json,subprocess,time,traceback,uuid
from pathlib import Path
from pg_support import Lab,Client,NO_WINDOW,literal,protect_directory,toolchain
from test_hardware_mounting_gui import fixture
from test_hardware_catalog17 import state,migrate,runtime_sql,CATALOG
from test_hardware_batch100c import BatchSession,ordered,payload,create_racks,catalog_rows,digest,verify_device
from test_hardware_selected506j import authoring as before_authoring

ROOT=Path(__file__).resolve().parents[3]
REVISION='selected506k-20261101-v1'
ALL_CATALOG=(*CATALOG,'hardware_connector_template')

def rows(lab,db,table):
    assert table in ALL_CATALOG
    return json.loads(lab.sql(db,f"SELECT COALESCE(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]') FROM {table} t"))

def checkpoint(lab,db):
    return (state(lab,db),rows(lab,db,'hardware_connector_template'))

def authoring():
    j,older,_=before_authoring();baseline=older+j
    plan=json.loads((ROOT/'evidence/s1-20261101/integracion506k/PLAN-FAMILIAS.json').read_text())
    models=[];pins={}
    for family in plan['authoring']:
        p=ROOT/f'development/hardware/selected506k/{family}.json';raw=p.read_bytes();data=json.loads(raw)
        assert data['revision']==REVISION
        models += [row['definition'] for row in data['models']]
        pins[p.relative_to(ROOT).as_posix()]=hashlib.sha256(raw).hexdigest()
    support=json.loads((ROOT/'development/hardware/selected506k/support.json').read_text())
    # Support is synthetic deployment data, not a commercial SKU or selection point.
    if 'definitions' in support:support=support['definitions'][0]
    elif 'definition' in support:support=support['definition']
    assert len(models)==52 and len(baseline)==752 and support['kind']=='shelf'
    assert len({m['key'] for m in models+baseline+[support]})==805
    assert {m['key'] for m in models}=={'selected-'+m['id'] for group in plan['authoring'].values() for m in group}
    return sorted(models,key=lambda m:m['key']),baseline,support,pins

def create_model(session,model,rack,name,definitions):
    parent=slot=None
    if model['kind']=='desktop':
        choices=[(s,slot) for s in definitions if s['kind']=='shelf' for slot in s['slots'] if all(model['dimensionsMm'][k]<=slot['dimensionsMm'][k] for k in ('width','height','depth'))]
        assert choices,model['key']
        s,sl=min(choices,key=lambda v:(v[0]['rackUnits'],v[0]['key']))
        parent=session.send(payload(s,rack,'Support '+name)).json()['result']['resourceId'];slot=sl['key']
    request=payload(model,rack,name,parent,slot);key=str(uuid.uuid4());revision=session.revision
    response=session.send(request,key=key,revision=revision).json()
    return dict(deviceId=response['result']['resourceId'],supportId=parent,request=request,requestId=key,expectedRevision=revision,response=response)

def verify_catalog(lab,db,models,support):
    assert lab.sql(db,'SELECT count(*) FROM hardware_definition')=='805'
    ds=rows(lab,db,'hardware_definition');gs=rows(lab,db,'hardware_group_template');pcs=rows(lab,db,'hardware_connector_template');ps=rows(lab,db,'hardware_passthrough');slots=rows(lab,db,'hardware_mount_slot')
    for m in models+[support]:
        pair=(m['key'],m['revision']);same=lambda x:(x['profile_key'],x['revision'])==pair
        d=next(d for d in ds if same(d));assert d['sealed'] and d['definition_sha256']==digest(m)
        assert (d['mount_kind'],d['rack_units'],d['width_mm'],d['height_mm'],d['depth_mm'])==(m['kind'],m['rackUnits'],m['dimensionsMm']['width'],m['dimensionsMm']['height'],m['dimensionsMm']['depth'])
        assert all(d[k]==m['identity'][k] for k in ('manufacturer','family','model','sku'))
        actual=sorted([g for g in gs if same(g)],key=lambda g:g['sort_order']);assert len(actual)==len(m['groups'])
        for order,(g,e) in enumerate(zip(actual,m['groups'])):
            assert (g['group_key'],g['sort_order'],g['type'],g['port_count'],g['face'],g['name'],g['prefix'],g['power_role'])==(e['key'],order,e['type'],e['count'],e['face'],e['name'],e['prefix'],e['powerRole'])
            pc=[x for x in pcs if same(x) and x['group_key']==e['key']]
            assert pc==([dict(profile_key=m['key'],revision=m['revision'],group_key=e['key'],physical_connector=e['physicalConnector'])] if e.get('physicalConnector') else [])
        continuity=m['passthrough'];actualp=[p for p in ps if same(p)]
        assert actualp==([dict(profile_key=m['key'],revision=m['revision'],front_group_key=continuity['frontGroup'],rear_group_key=continuity['rearGroup'],port_count=continuity['count'])] if continuity else [])
        actualslots=[s for s in slots if same(s)]
        assert len(actualslots)==len(m['slots'])
        for s,e in zip(actualslots,m['slots']):assert (s['slot_key'],s['width_mm'],s['height_mm'],s['depth_mm'])==(e['key'],e['dimensionsMm']['width'],e['dimensionsMm']['height'],e['dimensionsMm']['depth'])

def upgrade(lab,old_dll,dll,models,baseline,support,out):
    db=lab.create_database('selected506k-upgrade39');ids,password=fixture(lab,db,old_dll)
    assert lab.sql(db,'SELECT max(version) FROM schema_migration')=='39'
    commercial=[m for m in baseline if m['identity']['manufacturer']];assert len(commercial)==747
    racks=create_racks(lab,db,ids,['Preserve '+m['key'] for m in commercial]);lab.grant_runtime(db)
    server=lab.start_server(db,dll=old_dll);session=BatchSession(server,ids,password)
    for m,r in zip(commercial,racks):create_model(session,m,r['rack'],'Previous '+m['key'],baseline)
    expected=ordered(session.project());before=state(lab,db,catalog=False);stored={t:catalog_rows(lab,db,t) for t in CATALOG}
    history=lab.sql(db,'SELECT jsonb_agg(to_jsonb(t) ORDER BY version) FROM schema_migration t');server.close()
    assert migrate(lab,db,dll,out/'migration-private.txt')==0
    assert lab.sql(db,'SELECT max(version) FROM schema_migration')=='41'
    assert state(lab,db,catalog=False)==before
    assert lab.sql(db,'SELECT jsonb_agg(to_jsonb(t) ORDER BY version) FROM schema_migration t WHERE version<=39')==history
    for table in CATALOG:assert catalog_rows(lab,db,table,[m['key'] for m in baseline])==stored[table]
    assert not any(p['profile_key'] in {m['key'] for m in baseline} for p in rows(lab,db,'hardware_connector_template'))
    verify_catalog(lab,db,models,support);frozen=checkpoint(lab,db)
    assert migrate(lab,db,dll,out/'migration-repeat-private.txt')==0 and checkpoint(lab,db)==frozen
    lab.grant_runtime(db);server=lab.start_server(db,dll=dll);assert ordered(BatchSession(server,ids,password).project())==expected;server.close()
    return dict(sourceSchema=39,targetSchema=41,preservedDefinitions=752,preservedCommercialInstances=747,priorRowsAndHistoryUnchanged=True,sidecarDoesNotReclassifyOldDefinitions=True,repeatMigrationUnchanged=True)

def power_fixture(lab,db,ids,racks,models):
    house=lab.sql(db,'SELECT id FROM systemhaus');sql=['BEGIN;']
    for r,m in zip(racks,models):
        r['powerPeers']={}
        for role in ('inlet','outlet'):
            n=sum(g['count'] for g in m['groups'] if g['type']=='power' and g['powerRole']!=role)
            if not n:continue
            d,g=str(uuid.uuid4()),str(uuid.uuid4());r['powerPeers'][role]=[]
            sql.append(f"INSERT INTO inventory_device(id,systemhaus_id,customer_id,kind,rack_id,name,size_u,sort_order) VALUES({literal(d)},{literal(house)},{literal(ids['customer'])},'rackEquipment',{literal(r['rack'])},{literal('Synthetic '+role)},1,{len(r['powerPeers'])-1});")
            sql.append(f"INSERT INTO inventory_port_group(id,systemhaus_id,customer_id,device_id,type,name,prefix,sort_order) VALUES({literal(g)},{literal(house)},{literal(ids['customer'])},{literal(d)},'power',{literal(role)},'AC ',0);")
            for i in range(n):
                p=str(uuid.uuid4());r['powerPeers'][role].append(p)
                sql.append(f"INSERT INTO inventory_port(id,systemhaus_id,customer_id,device_id,group_id,type,gn,sort_order,face,power_role) VALUES({literal(p)},{literal(house)},{literal(ids['customer'])},{literal(d)},{literal(g)},'power',{i+1},{i},'rear',{literal(role)});")
    sql.append('COMMIT;');lab.sql(db,'\n'.join(sql),sensitive=True)

def fresh(lab,dll,frontend,models,baseline,support,out,browser):
    db=lab.create_database('selected506k-fresh41');ids,password=fixture(lab,db,dll);verify_catalog(lab,db,models,support)
    racks=create_racks(lab,db,ids,['Selection '+m['identity']['sku'] for m in models]);power_fixture(lab,db,ids,racks,models);lab.grant_runtime(db)
    server=lab.start_server(db,dll=dll,frontend=frontend);session=BatchSession(server,ids,password);definitions=baseline+[support]
    entries=[];measured=[];replays=[];counts=Counter();gui_pairs=[];gui_types=set()
    for m,r in zip(models,racks):
        a=create_model(session,m,r['rack'],m['identity']['model'],definitions);b=create_model(session,m,r['rack'],'Peer '+m['identity']['sku'],definitions);project=session.project()
        own=verify_device(project,m,a['deviceId'],r['rack'],a['supportId']);peer=verify_device(project,m,b['deviceId'],r['rack'],b['supportId'])
        for g in m['groups']:
            for p in own[g['key']]+peer[g['key']]:assert p['properties'].get('hardwarePhysicalConnector')==g.get('physicalConnector')
        if m['passthrough']:
            x=next(d for d in project['devices'] if d['id']==a['deviceId']);c=m['passthrough']
            assert x['properties']['declaredPassthrough']==dict(fromGroupKey=c['frontGroup'],toGroupKey=c['rearGroup'],rule='sameOrdinal',tracingImplemented=False)
        used_power=Counter();wires=[];seen=set()
        for g in m['groups']:
            t=g['type']
            if t!='power' and t in seen:continue
            seen.add(t)
            ports=own[g['key']] if t=='power' else own[g['key']][:1]
            for p in ports:
                if t=='power':
                    role='outlet' if p['powerRole']=='inlet' else 'inlet';target=r['powerPeers'][role][used_power[role]];used_power[role]+=1
                else:target=peer[g['key']][0]['id']
                pair=dict(type=t,rack=r['rack'],fromPortId=p['id'],toPortId=target,face=p['face'])
                if t not in gui_types and (t!='power' or p['face']=='rear'):gui_types.add(t);gui_pairs.append(pair);continue
                response=session.send(dict(fromPortId=p['id'],toPortId=target),kind='connections.create').json();wires.append(pair|dict(id=response['result']['resourceId']));counts[t]+=1
        entries.append(dict(key=m['key'],rack=r['rack'],deviceId=a['deviceId'],peerId=b['deviceId'],kind=m['kind'],portCount=sum(g['count'] for g in m['groups'])))
        measured.append(dict(key=m['key'],ports=entries[-1]['portCount'],connections=wires,uuidFaceRoleOrdinalAndDescriptorMatched=True));replays.append(a)
    assert gui_types=={'rj45','console','idc','power'}
    # A generic cord may have dissimilar ends. Classification must not silently
    # add a direct-mating gate to the existing inlet/outlet power policy.
    peer_ids={e['peerId'] for e in entries};project=session.project()
    c19=next(p for p in project['ports'] if p['deviceId'] in peer_ids and p['powerRole']=='outlet' and p['properties'].get('hardwarePhysicalConnector')=='iec-c19')
    c14=next(p for p in project['ports'] if p['deviceId'] in peer_ids and p['powerRole']=='inlet' and p['properties'].get('hardwarePhysicalConnector')=='iec-c14')
    session.send(dict(fromPortId=c19['id'],toPortId=c14['id'],note='Generic cord; ends/electrical suitability unspecified'),kind='connections.create');counts['power']+=1
    # Actual CSV and XLSX preserve typed optional physical description. The
    # frontend's complete byte/hash/header validators must accept these responses.
    report_rack=next(e['rack'] for e in entries if any(g['type']=='idc' for g in next(m for m in models if m['key']==e['key'])['groups']) and not any(p['type']=='idc' and p['rack']==e['rack'] for p in gui_pairs))
    reports=[]
    for format in ('csv','xlsx'):
        for kind in ('ports','connections'):
            f=dict(reportKind=kind,query='',status='all',family='all',rackId=report_rack);request_id=str(uuid.uuid4())
            response=session.client.request('POST',session.route+'/reports/'+format,f,{'X-RackClick-Actor':session.actor,'If-Match':f'\"{session.revision}\"','Idempotency-Key':request_id})
            assert response.status==200,(format,kind,response.status,response.body)
            reports.append(dict(format=format,kind=kind,data=response.json(),operation=dict(actorId=session.actor,customerId=ids['customer'],revision=session.revision,requestId=request_id,body=json.dumps(f))))
    (out/'reports-private.json').write_text(json.dumps(reports))
    with (out/'reports-validator-private.log').open('wb') as log:validated=subprocess.run([str(toolchain()['node']),str(ROOT/'development/frontend/tests/validate-hardware-family-reports.mjs'),str(out/'reports-private.json'),str(out/'REPORTS-VALIDATED.json')],cwd=ROOT/'development/frontend',stdout=log,stderr=log,timeout=30,creationflags=NO_WINDOW)
    assert validated.returncode==0,'Actual report validation failed; private log retained'
    expected=ordered(session.project());before=checkpoint(lab,db)
    # The sidecar is immutable for the migration owner as well as read-only for
    # runtime. A failed operation must preserve every row, audit and operation.
    for sql in ('UPDATE hardware_connector_template SET physical_connector=physical_connector','DELETE FROM hardware_connector_template','TRUNCATE hardware_connector_template'):
        try:lab.sql(db,sql)
        except RuntimeError as error:assert 'sealed' in str(error).lower() or 'immutable' in str(error).lower(),str(error)
        else:raise AssertionError('Owner mutation unexpectedly accepted: '+sql)
        assert checkpoint(lab,db)==before
    for original in replays[:2]:assert session.send(original['request'],key=original['requestId'],revision=original['expectedRevision']).json()==original['response'] and checkpoint(lab,db)==before
    def reject(command,kind,status,error):
        response=session.send(command,kind=kind,status=status);assert response.json()['error']==error,(response.body,error);assert checkpoint(lab,db)==before
    # Reserved metadata cannot be changed, forged or removed (including JSON null).
    sample=next(p for p in expected['ports'] if p['properties'].get('hardwarePhysicalConnector'))
    for value in ('serial-8p8c',None):
        reject(dict(deviceId=sample['deviceId'],groupId=sample['groupId'],groupType=sample['type'],portIds=[sample['id']],changes={'properties':{'hardwarePhysicalConnector':value}}),'ports.update',422,'hardware_metadata_immutable')
    # Cross-media rejection is external only: IDC↔IDC and console↔console work,
    # but the panel declaration never creates RJ45↔IDC patch cables implicitly.
    typed={t:next(p for p in expected['ports'] if p['type']==t) for t in ('rj45','console','idc','power')}
    for left,right in [('rj45','console'),('rj45','idc'),('idc','console'),('power','console')]:reject(dict(fromPortId=typed[left]['id'],toPortId=typed[right]['id']),'connections.create',409,'connection_incompatible')
    rack_index=next(i for i,m in enumerate(models) if m['kind']=='rack');request=payload(models[rack_index],racks[rack_index]['rack'],'Must rollback')
    lab.sql(db,"CREATE FUNCTION selected506k_fail_audit() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic audit failure'; END $$; CREATE TRIGGER selected506k_fail_audit BEFORE INSERT ON audit_event FOR EACH ROW EXECUTE FUNCTION selected506k_fail_audit()")
    try:
        response=session.client.request('POST',session.route+'/commands',{'type':'device.createHardware','payload':request},{'X-RackClick-Actor':session.actor,'If-Match':f'\"{session.revision}\"','Idempotency-Key':str(uuid.uuid4())});assert response.status>=500 and checkpoint(lab,db)==before
    finally:lab.sql(db,'DROP TRIGGER selected506k_fail_audit ON audit_event; DROP FUNCTION selected506k_fail_audit()')
    assert session.send(request,revision=session.revision-1,status=412).json()['error']=='revision_conflict' and checkpoint(lab,db)==before
    reject(request|dict(profileVersion='latest'),'device.createHardware',422,'hardware_revision_unknown')
    reader=Client(server);assert reader.login('hardware-reader',password).status==200;actor=reader.request('GET','/api/v1/me').json()['user']['id']
    response=reader.request('POST',session.route+'/commands',{'type':'device.createHardware','payload':request},{'X-RackClick-Actor':actor,'If-Match':f'\"{session.revision}\"','Idempotency-Key':str(uuid.uuid4())});assert response.status==403 and checkpoint(lab,db)==before
    for table in ALL_CATALOG:
        rights=runtime_sql(lab,db,f"SELECT has_table_privilege(current_user,'{table}','SELECT'),has_table_privilege(current_user,'{table}','INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')");assert rights.returncode==0 and rights.stdout.strip()=='t|f'
    assert runtime_sql(lab,db,'CREATE TABLE must_not_exist(id integer)').returncode!=0
    second=Client(server);assert second.login('hardware-second',password).status==200;assert ordered(second.request('GET',session.route+'/project').json())==expected
    ids['selected506k']=entries;ids['guiPairs']=gui_pairs
    fixture_json=json.dumps(ids,ensure_ascii=True,separators=(',',':'));assert len(fixture_json.encode())<24000
    (out/'fixture-ids.json').write_text(fixture_json);(out/'expected-project.json').write_text(json.dumps(expected))
    if browser:
        env=lab.environment();env.update(RACKCLICK_TEST_ORIGIN=server.origin,RACKCLICK_TEST_USERNAME='hardware-admin',RACKCLICK_TEST_PASSWORD=password,RACKCLICK_TEST_OUTPUT=str(out),RACKCLICK_FIXTURE=fixture_json)
        with (out/'browser-private.log').open('wb') as log:done=subprocess.run([str(toolchain()['node']),str(ROOT/'development/frontend/tests/browser-hardware-selected506k.mjs')],cwd=ROOT/'development/frontend',env=env,stdout=log,stderr=log,timeout=900,creationflags=NO_WINDOW)
        assert done.returncode==0,'Browser failed; private log retained';expected=ordered(json.loads((out/'expected-browser-project.json').read_text()));assert ordered(session.project())==expected
    server.close();server=lab.start_server(db,dll=dll,frontend=frontend);second=Client(server);assert second.login('hardware-second',password).status==200;assert ordered(second.request('GET',session.route+'/project').json())==expected
    return dict(schema=41,modelsCreated=52,modelPorts=sum(e['portCount'] for e in entries),modelResults=measured,connections=sum(counts.values()),cablesByType=dict(counts),guiConnectionsAdded=4 if browser else 0,browserExecuted=browser,independentPeerInstances=52,replayVerified=True,rollbackVerified=True,conflictRejected=True,readerRejected=True,runtimeCatalogSelectOnly=True,sidecarOwnerMutationsRejected=3,mixedCordC19ToC14Accepted=True,actualCsvAndXlsxValidated=4,reservedMetadataRejected=True,crossTypeRejections=4,secondSessionEqual=True,restartPersistence=True)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('dll','baseline-dll','frontend','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--browser',action='store_true');parser.add_argument('--upgrade-evidence',type=Path);a=parser.parse_args();out=a.output.resolve();assert out.is_relative_to((ROOT/'.local').resolve()) and not out.exists();out.mkdir(parents=True);protect_directory(out)
    models,baseline,support,pins=authoring();result=dict(result='FAIL',vmAccessed=False,qaAccessed=False,sourceSha256=pins);start=time.monotonic();lab=None
    try:
        lab=Lab('hardware-selected506k')
        with lab:
            if a.upgrade_evidence:
                path=a.upgrade_evidence.resolve();assert path.is_relative_to((ROOT/'.local').resolve());previous=json.loads(path.read_text());artifacts=json.loads((path.parent.parent/'ARTIFACTS-FINAL.json').read_text());prior=json.loads((path.parent.parent/'BASELINE.json').read_text())
                assert hashlib.sha256(a.dll.read_bytes()).hexdigest()==artifacts['serverSha256'] and hashlib.sha256(a.baseline_dll.read_bytes()).hexdigest()==prior['serverSha256']
                assert previous['sourceSha256']==pins and previous['upgrade']['targetSchema']==41 and previous['upgrade']['preservedCommercialInstances']==747 and previous['labStopped'] and previous['serversStopped']
                result['upgrade']=previous['upgrade'];result['upgradeEvidence']=dict(path=path.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),reexecuted=False,reason='Identical backend/baseline/model bytes; original upgrade passed, fresh fixture sort_order was corrected.')
            else:result['upgrade']=upgrade(lab,a.baseline_dll,a.dll,models,baseline,support,out)
            result.update(fresh(lab,a.dll,a.frontend,models,baseline,support,out,a.browser));assert all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==p for n,p in pins.items());result.update(result='PASS',postgresql=lab.sql('postgres','SHOW server_version'))
    except BaseException as error:result.update(failureType=type(error).__name__);(out/'runner-private.log').write_text(traceback.format_exc(),encoding='utf-8')
    finally:
        result.update(elapsedSeconds=round(time.monotonic()-start,3),labStopped=lab is None or not lab.running,serversStopped=lab is None or all(s.process.poll() is not None for s in lab.servers));(out/'RESULTADOS.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ('result','modelsCreated','modelPorts','connections','browserExecuted','labStopped','serversStopped','failureType') if k in result}))
    return 0 if result['result']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
