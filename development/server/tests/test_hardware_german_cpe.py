"""German CPE44 on NEW PostgreSQL17 labs; optional exact schema43 upgrade.

No VM, Windows services, real credentials or installed instance is touched.
One fresh host and one restart; raw SQL/session fixtures remain private.
"""
import argparse,hashlib,json,subprocess,time,traceback,uuid
from pathlib import Path
from pg_support import Lab,Client,literal,protect_directory
from test_hardware_mounting_gui import fixture
from test_hardware_catalog17 import migrate
from test_hardware_batch100c import BatchSession,ordered,payload,create_racks,digest
from test_hardware_selected506k import create_model
ROOT=Path(__file__).resolve().parents[3]
TABLES=('hardware_definition','hardware_mount_slot','hardware_group_template','hardware_passthrough','hardware_connector_template','hardware_profile_extension','hardware_group_extension')
class TrialLab(Lab):
    def environment(self):
        env=super().environment();env.update(MfaKeyStore__Enabled='false',SqlSecret__Enabled='false');return env
    def bootstrap(self,database,username,password,dll=None):
        r=super().bootstrap(database,username,password,dll)
        (database.directory/'bootstrap-private.log').write_text(r.stdout+'\n'+r.stderr,encoding='utf-8')
        return r
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def definitions():
    return sorted([r['definition'] for n in ['fritz','draytek'] for r in json.loads((ROOT/f'development/hardware/german-cpe/{n}.json').read_bytes())['models']],key=lambda d:d['key'])
def catalogue(lab,db):
    return {t:json.loads(lab.sql(db,f"SELECT COALESCE(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]') FROM {t} t")) for t in TABLES}
def upgrade(lab,old,dll,out):
    db=lab.create_database('german-upgrade43');ids,pw=fixture(lab,db,old)
    oldcat=catalogue(lab,db);assert len(oldcat['hardware_definition'])==868
    history=lab.sql(db,'SELECT jsonb_agg(to_jsonb(t) ORDER BY version) FROM schema_migration t')
    before=lab.sql(db,'SELECT jsonb_agg(to_jsonb(t) ORDER BY id) FROM inventory_device t')
    assert migrate(lab,db,dll,out/'upgrade43-private.log')==0
    newcat=catalogue(lab,db);oldpairs={(r['profile_key'],r['revision']) for r in oldcat['hardware_definition']}
    assert len(newcat['hardware_definition'])==874
    for t,rows in oldcat.items():assert [r for r in newcat[t] if (r['profile_key'],r['revision']) in oldpairs]==rows,t
    assert lab.sql(db,'SELECT jsonb_agg(to_jsonb(t) ORDER BY version) FROM schema_migration t WHERE version<=43')==history
    assert lab.sql(db,'SELECT jsonb_agg(to_jsonb(t) ORDER BY id) FROM inventory_device t')==before
    assert migrate(lab,db,dll,out/'repeat44-private.log')==0
    assert catalogue(lab,db)==newcat
    return dict(upgrade43to44=True,prior868DefinitionsUnchanged=True,history43Unchanged=True,inventoryUnchanged=True,repeatMigrationIdempotent=True)
def main():
    p=argparse.ArgumentParser();p.add_argument('--dll',type=Path,required=True);p.add_argument('--baseline-dll',type=Path,required=True);p.add_argument('--frontend',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.dll=a.dll.resolve(strict=True);a.baseline_dll=a.baseline_dll.resolve(strict=True);a.frontend=a.frontend.resolve(strict=True)
    out=a.output.absolute();assert out.is_relative_to((ROOT/'.local').absolute()) and not out.exists();out.mkdir(parents=True);protect_directory(out)
    result=dict(result='FAIL',vmAccessed=False,qaAccessed=False,serverSha256=sha(a.dll),baselineSha256=sha(a.baseline_dll),frontendSha256=sha(a.frontend/'app.js'));lab=TrialLab('german-cpe44');stage='upgrade'
    try:
      models=definitions();assert len(models)==6
      with lab:
        result.update(upgrade(lab,a.baseline_dll,a.dll,out));stage='fresh'
        db=lab.create_database('german-fresh44');ids,pw=fixture(lab,db,a.dll)
        assert lab.sql(db,'SELECT max(version) FROM schema_migration')=='44'
        assert lab.sql(db,'SELECT count(*) FROM hardware_definition')=='874'
        supports=json.loads((ROOT/'development/hardware/catalog-source-v1.json').read_bytes())['definitions']
        # Existing5U fixture selection envelope; server checks its actual immutable slot.
        supports+= [dict(key='shelf-5u',revision='mount-support-20261030-v1',kind='shelf',rackUnits=5,slots=[dict(key='main',dimensionsMm=dict(width=440,height=210,depth=500))])]
        racks=create_racks(lab,db,ids,['CPE '+m['key'] for m in models]+['Peer '+m['key'] for m in models])
        lab.grant_runtime(db);server=lab.start_server(db,dll=a.dll,frontend=a.frontend);s=BatchSession(server,ids,pw);stage='create'
        entries=[]
        for i,m in enumerate(models):
            a1=create_model(s,m,racks[i]['rack'],'CPE '+m['identity']['model'],supports)
            peer=create_model(s,m,racks[i+6]['rack'],'Peer '+m['identity']['model'],supports)
            entries.append((m,a1,peer))
        project=s.project();allids=[r['id'] for k in ('devices','portGroups','ports') for r in project[k]];assert len(allids)==len(set(allids))
        checks=[];pairs={}
        for m,a1,peer in entries:
            ports=[p for p in project['ports'] if p['deviceId']==a1['deviceId']];assert len(ports)==sum(g['count'] for g in m['groups'])
            for g in m['groups']:
                actual=sorted([p for p in ports if p['properties'].get('hardwareGroupKey')==g['key']],key=lambda p:p['gn'])
                assert len(actual)==g['count']
                for ordinal,port in enumerate(actual,1):
                    assert (port['type'],port['gn'],port['face'],port['powerRole'])==(g['type'],ordinal,g['face'],g['powerRole'])
                    assert port['properties'].get('hardwarePhysicalConnector')==g.get('physicalConnector')
                if g['type'] not in pairs and g['type']!='power_dc':
                    pp=next(p for p in project['ports'] if p['deviceId']==peer['deviceId'] and p['properties'].get('hardwareGroupKey')==g['key'] and p['gn']==1)
                    pairs[g['type']]=(actual[0]['id'],pp['id'])
            checks.append(dict(key=m['key'],deviceId=a1['deviceId'],portCount=len(ports),uuidGroupsFacesRolesAndMetadata=True))
        stage='connections';cables=[]
        for typ,(a2,b2) in pairs.items():cables.append(dict(type=typ,id=s.send(dict(fromPortId=a2,toPortId=b2),kind='connections.create').json()['result']['resourceId']))
        before=ordered(s.project());dsl=next(p for p in before['ports'] if p['type']=='dsl' and not any(p['id'] in pair for pair in pairs.values()));eth=next(p for p in before['ports'] if p['type']=='rj45' and not any(p['id'] in pair for pair in pairs.values()))
        s.send(dict(fromPortId=dsl['id'],toPortId=eth['id']),kind='connections.create',status=409);assert ordered(s.project())==before
        # A reader can inspect the saved endpoints but cannot create catalogue objects.
        reader=Client(server);assert reader.login('hardware-reader',pw).status==200
        actor=reader.request('GET','/api/v1/me').json()['user']['id']
        denied=reader.request('POST',s.route+'/commands',dict(type='device.createHardware',payload=entries[0][1]['request']),{'X-RackClick-Actor':actor,'If-Match':f'"{s.revision}"','Idempotency-Key':str(uuid.uuid4())});assert denied.status==403
        assert ordered(reader.request('GET',s.route+'/project').json())==before
        replay=entries[0][1];assert s.send(replay['request'],key=replay['requestId'],revision=replay['expectedRevision']).json()==replay['response'];assert ordered(s.project())==before
        second=Client(server);assert second.login('hardware-second',pw).status==200;assert ordered(second.request('GET',s.route+'/project').json())==before
        stage='restart';server.close();server=lab.start_server(db,dll=a.dll,frontend=a.frontend);again=Client(server);assert again.login('hardware-second',pw).status==200;assert ordered(again.request('GET',s.route+'/project').json())==before
        assert lab.sql(db,f"SELECT has_schema_privilege('{db.runtime}','public','CREATE')")=='f'
        assert lab.sql(db,f"SELECT has_table_privilege('{db.runtime}','hardware_definition','INSERT')")=='f'
        result.update(result='PASS',schema=44,postgresql=lab.sql('postgres','SHOW server_version'),modelsCreated=6,peerInstances=6,modelPorts=51,modelResults=checks,connections=cables,reader403=True,reloadSecondSessionAndRestart=True,replayIdempotent=True,wrongMedia409NoMutation=True,runtimeNoDDLAndCatalogueReadOnly=True)
    except BaseException as e:
        result.update(failureStage=stage,failureType=type(e).__name__);(out/'private-error.log').write_text(traceback.format_exc(),encoding='utf-8')
    finally:
        result.update(labStopped=not lab.running,serversStopped=all(s.process.poll() is not None for s in lab.servers));(out/'RESULTADOS.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ('result','schema','modelsCreated','modelPorts','failureStage','failureType','labStopped','serversStopped') if k in result}))
    return 0 if result['result']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
