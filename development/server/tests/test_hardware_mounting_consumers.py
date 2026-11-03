"""Hardware geometry immutability and legacy export boundaries, real PG17/HTTP."""
import argparse, base64, json, uuid
from pathlib import Path
from pg_support import Lab, Client, protect_directory
from test_hardware_mounting import setup, state

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--dll',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);a=parser.parse_args()
    dll=a.dll.resolve(strict=True);a.output.mkdir(parents=True,exist_ok=False);protect_directory(a.output)
    report={'result':'FAIL','qaChanged':False,'checks':[]};lab=Lab('hardware-consumers')
    try:
        with lab:
            db=lab.create_database();ids,password=setup(lab,db,dll);server=lab.start_server(db,dll=dll);client=Client(server);assert client.login('hardware-admin',password).status==200
            actor=client.request('GET','/api/v1/me').json()['user']['id'];prefix=f"/api/v1/customers/{ids['customer']}"
            def project():return client.request('GET',prefix+'/project').json()
            def send(route,payload):return client.request('POST',prefix+route,payload,{'X-RackClick-Actor':actor,'If-Match':f'"{project()["revision"]}"','Idempotency-Key':str(uuid.uuid4())})
            def command(kind,payload,status=200):
                r=send('/commands',{'type':kind,'payload':payload});assert r.status==status,(r.status,r.body);return r.json()
            shelf=command('device.createHardware',{'profileKey':'shelf-2u','rackId':ids['rack'],'name':'Shelf reference'})['result']['resourceId']
            fw=command('device.createHardware',{'profileKey':'desktop-firewall-6','rackId':ids['rack'],'name':'Firewall <literal>','mountParentId':shelf,'mountSlotKey':'main'})['result']['resourceId']
            port=next(p for p in project()['ports'] if p['deviceId']==fw and p['face']=='front');batch={'deviceId':fw,'groupId':port['groupId'],'groupType':'rj45','portIds':[port['id']]}
            before=state(lab,db)
            result=command('ports.update',{**batch,'changes':{'face':'rear'}},422);assert result['error']=='hardware_metadata_immutable';assert state(lab,db)==before
            report['checks'].append('profile connector face cannot be changed; exact inventory/revision/operation/audit unchanged')
            command('ports.update',{**batch,'changes':{'face':'front','status':'reserved','label':'Saved label Ω'}})
            actual=next(p for p in project()['ports'] if p['id']==port['id']);assert actual['face']=='front' and actual['status']=='reserved' and actual['label']=='Saved label Ω'
            report['checks'].append('same face plus editable status/label persist normally')
            for route,payload in [('/reports/rack-svg',{'rackId':ids['rack'],'face':'front','language':'es'}),('/reports/xls-html',{'rackId':ids['rack']})]:
                before=state(lab,db);r=send(route,payload);assert r.status==422 and r.json()['error']=='report_mounting_unsupported';assert state(lab,db)==before
            report['checks'].append('SVG and RC9 HTML-XLS reject an unrepresentable mounted scope without partial exports or audit/operation mutations')
            r=send('/reports/printable',{'reportKind':'rack','rackIds':[ids['rack']],'language':'es'});assert r.status==200,(r.status,r.body)
            html=base64.b64decode(r.json()['report']['contentBase64']).decode('utf-8');assert 'U adicionales; montado sobre' in html and shelf in html and 'Firewall &lt;literal&gt;' in html
            report['checks'].append('printable inventory labels zero additional U, owning shelf UUID and escaped literal name')
            # The same formats still work for a normal root without a mounted child.
            command('device.createHardware',{'profileKey':'switch-24','rackId':ids['extra'],'name':'Normal switch'})
            for route,payload in [('/reports/rack-svg',{'rackId':ids['extra'],'face':'rear','language':'de'}),('/reports/xls-html',{'rackId':ids['extra']})]:
                r=send(route,payload);assert r.status==200,(r.status,r.body)
            report['checks'].append('normal root-only scopes still export SVG and HTML-XLS')
            report.update(result='PASS',postgresql=lab.sql('postgres','SHOW server_version'))
    finally:
        report.update(labStopped=not lab.running,serversStopped=all(s.process.poll() is not None for s in lab.servers));(a.output/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,indent=2))
    return 0 if report['result']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
