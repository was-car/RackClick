"""Focused real-PG transaction test: explicit rack impact removes the complete mounted assembly, never other racks."""
import argparse, hashlib, json, sys, time, uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'development/server/tests'))
from pg_support import Lab,Client
from test_hardware_mounting import setup,state

def main():
    p=argparse.ArgumentParser();p.add_argument('--dll',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    dll=a.dll.resolve(strict=True);a.output.mkdir(parents=True,exist_ok=False)
    result={'result':'FAIL','qaAccessed':False,'vmAccessed':False,'serverSha256':hashlib.sha256(dll.read_bytes()).hexdigest()}
    lab=Lab('hardware-delete');tick=time.monotonic()
    try:
        with lab:
            db=lab.create_database('hardware-delete');ids,password=setup(lab,db,dll);server=lab.start_server(db,dll=dll);client=Client(server);assert client.login('hardware-admin',password).status==200
            route=f"/api/v1/customers/{ids['customer']}/commands";projectRoute=f"/api/v1/customers/{ids['customer']}/project";actor=client.request('GET','/api/v1/me').json()['user']['id']
            def project():return client.request('GET',projectRoute).json()
            def command(kind,payload,status=200):
                reply=client.request('POST',route,{'type':kind,'payload':payload},{'If-Match':f'"{project()["revision"]}"','Idempotency-Key':str(uuid.uuid4()),'X-RackClick-Actor':actor})
                assert reply.status==status,(kind,reply.status,reply.body.decode());return reply.json()
            for key,profile in [('shelf','shelf-2u'),('firewall','desktop-firewall-6'),('switch','switch-24'),('patch','patchpanel-24')]:
                payload={'profileKey':profile,'rackId':ids['rack'],'name':key}
                if key=='firewall':payload.update(mountParentId=ids['shelf'],mountSlotKey='main')
                ids[key]=command('device.createHardware',payload)['result']['resourceId']
            def port(device,face,gn):return next(p['id'] for p in project()['ports'] if p['deviceId']==ids[device] and p['face']==face and p['gn']==gn)
            for ends in [(('firewall','front',1),('switch','front',1)),(('switch','front',2),('patch','front',1)),(('patch','rear',1),('firewall','rear',1))]:
                command('connections.create',{'fromPortId':port(*ends[0]),'toPortId':port(*ends[1])})
            before=project();atomic=state(lab,db);rev=before['revision']
            headers={'If-Match':f'"{rev}"','X-RackClick-Actor':actor}
            preview=client.request('POST',route+'/preview',{'type':'rack.delete','payload':{'id':ids['rack']}},headers)
            assert preview.status==200,preview.body.decode();impact=preview.json()['impact']
            assert {k:len(v) for k,v in impact.items()}=={'rackIds':1,'deviceIds':4,'groupIds':6,'portIds':81,'connectionIds':3}
            assert set(impact['deviceIds'])=={ids[k] for k in ['shelf','firewall','switch','patch']}
            assert state(lab,db)==atomic,'Preview must be read-only'
            command('rack.delete',{'id':ids['rack'],'confirmationToken':'incorrect'},status=409);assert state(lab,db)==atomic
            command('rack.delete',{'id':ids['rack'],'confirmationToken':preview.json()['confirmationToken']})
            after=project();assert after['revision']==rev+1
            assert ids['rack'] not in {r['id'] for r in after['racks']} and ids['extra'] in {r['id'] for r in after['racks']}
            assert not after['devices'] and not after['portGroups'] and not after['ports'] and not after['connections']
            assert lab.sql(db,f"SELECT count(*) FROM inventory_rack WHERE id='{ids['foreign']}'")=='1'
            assert lab.sql(db,"SELECT count(*) FROM audit_event WHERE action='inventory.rack.delete'")=='1'
            server.close();restart=lab.start_server(db,dll=dll);reader=Client(restart);assert reader.login('hardware-reader',password).status==200
            observed=reader.request('GET',projectRoute);assert observed.status==200 and observed.json()==after
            result.update(result='PASS',postgresql=lab.sql('postgres','SHOW server_version'),impactCounts={k:len(v) for k,v in impact.items()},previewReadOnly=True,incorrectConfirmationRejected=True,remainingRackPreserved=True,otherCustomerPreserved=True,oneRevisionAndAudit=True,restartPersistence=True)
    except Exception as error:result.update(errorType=type(error).__name__,error=str(error))
    finally:
        result.update(seconds=round(time.monotonic()-tick,3),labStopped=not lab.running,serversStopped=all(s.process.poll() is not None for s in lab.servers))
        (a.output/'RESULTADOS.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,indent=2))
    return 0 if result['result']=='PASS' and result['labStopped'] and result['serversStopped'] else 1

if __name__=='__main__':raise SystemExit(main())
