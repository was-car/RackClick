"""Explicit/legacy revision requests, real PG17, unchanged schema16."""
import argparse, hashlib, json, uuid
from pathlib import Path
from pg_support import Lab, Client, protect_directory, literal
from test_hardware_mounting import setup, state

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--dll',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);a=parser.parse_args()
    dll=a.dll.resolve(strict=True);a.output.mkdir(parents=True,exist_ok=False);protect_directory(a.output)
    result={'result':'FAIL','schemaChanged':False,'qaChanged':False,'checks':[],'serverSha256':hashlib.sha256(dll.read_bytes()).hexdigest()};lab=Lab('hardware-revisions')
    try:
        with lab:
            db=lab.create_database();ids,password=setup(lab,db,dll);server=lab.start_server(db,dll=dll);client=Client(server);assert client.login('hardware-admin',password).status==200
            prefix=f"/api/v1/customers/{ids['customer']}";actor=client.request('GET','/api/v1/me').json()['user']['id']
            def project():return client.request('GET',prefix+'/project').json()
            def command(payload,status=200,key=None,revision=None):
                r=client.request('POST',prefix+'/commands',{'type':'device.createHardware','payload':payload},{'X-RackClick-Actor':actor,'If-Match':f'"{project()["revision"] if revision is None else revision}"','Idempotency-Key':key or str(uuid.uuid4())});assert r.status==status,(r.status,r.body);return r
            explicit={'profileKey':'shelf-2u','profileVersion':'hw-reference-v1','rackId':ids['rack'],'name':'Pinned shelf'};request=str(uuid.uuid4());rev=project()['revision']
            made=command(explicit,key=request,revision=rev).json();shelf=made['result']['resourceId'];before=state(lab,db)
            assert command(explicit,key=request,revision=rev).json()==made;assert state(lab,db)==before
            result['checks'].append('explicit v1 revision creates once; identical replay returns same operation, no new rows/audit/revision')
            # Existing callers omit the added field and remain pinned to the frozen v1.
            fw=command({'profileKey':'desktop-firewall-6','rackId':ids['rack'],'name':'Historical request','mountParentId':shelf,'mountSlotKey':'main'}).json()['result']['resourceId']
            snapshot=project();assert all(d['properties']['hardwareProfileVersion']=='hw-reference-v1' for d in snapshot['devices'])
            child=next(d for d in snapshot['devices'] if d['id']==fw);assert child['mountParentId']==shelf and child['properties']['physicalDimensionsMm']=={'width':220,'height':38,'depth':200}
            result['checks'].append('historical omitted-version request remains v1 with physical dimensions and parent identity')
            before=state(lab,db)
            for bad in [None,'','latest','hw-reference-v2','HW-REFERENCE-V1','hw-reference-v1 ',{},7]:
                command({'profileKey':'switch-24','profileVersion':bad,'rackId':ids['extra'],'name':'Rejected'},422)
                assert state(lab,db)==before
            result['checks'].append('eight invalid revisions reject before materialization; exact nine-table state unchanged')
            empty=command({'profileKey':'shelf-2u','profileVersion':'hw-reference-v1','rackId':ids['extra'],'name':'Fixture for unavailable parent'}) .json()['result']['resourceId']
            # Fixture-only owner edits emulate unavailable/malformed historical metadata;
            # the public API cannot perform these changes.
            for unavailable in ['missing-revision',None,{},7]:
                lab.sql(db,f"UPDATE inventory_device SET properties=jsonb_set(properties,'{{hardwareProfileVersion}}',{literal(json.dumps(unavailable))}::jsonb) WHERE id='{empty}'",sensitive=True)
                before=state(lab,db)
                r=command({'profileKey':'desktop-firewall-6','profileVersion':'hw-reference-v1','rackId':ids['extra'],'name':'Must not assume v1 bay','mountParentId':empty,'mountSlotKey':'main'},409)
                assert r.json()['error']=='mount_support_revision_unavailable';assert state(lab,db)==before
            lab.sql(db,f"UPDATE inventory_device SET properties=jsonb_set(properties,'{{hardwareProfileVersion}}','\"hw-reference-v1\"'::jsonb) WHERE id='{empty}'",sensitive=True)
            result['checks'].append('unknown/null/malformed parent revision cannot silently inherit the v1 bay; four atomic rejections')
            before=state(lab,db)
            # The version cannot be rewritten through generic metadata editing.
            r=client.request('POST',prefix+'/commands',{'type':'device.update','payload':{'id':fw,'properties':{'hardwareProfileVersion':'hw-reference-v2'}}},{'X-RackClick-Actor':actor,'If-Match':f'"{project()["revision"]}"','Idempotency-Key':str(uuid.uuid4())});assert r.status==422;assert state(lab,db)==before
            result['checks'].append('generic metadata update cannot replace the stored revision')
            snapshot=project()
            server.close();restart=lab.start_server(db,dll=dll);other=Client(restart);assert other.login('hardware-reader',password).status==200
            assert other.request('GET',prefix+'/project').json()==snapshot
            assert lab.sql(db,'SELECT max(version) FROM schema_migration')=='16'
            result.update(result='PASS',postgresql=lab.sql('postgres','SHOW server_version'),restartPersistence=True,checksPassed=len(result['checks']))
    finally:
        result.update(labStopped=not lab.running,serversStopped=all(s.process.poll() is not None for s in lab.servers));(a.output/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,indent=2))
    return 0 if result['result']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
