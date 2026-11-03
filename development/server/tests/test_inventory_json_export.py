"""Current-inventory JSON export against a NEW PostgreSQL17 lab. No installed DB/QA/VM."""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import time
import traceback
import uuid
from pg_support import Lab, Client, literal, protect_directory, toolchain, NO_WINDOW
from test_hardware_mounting_gui import fixture
from test_hardware_batch100c import BatchSession, ordered

ROOT=Path(__file__).resolve().parents[3]
COLLECTIONS=('sites','buildings','rooms','racks','devices','portGroups','ports','connections')
BODY={'formatVersion':1,'scope':'customer'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('dll','frontend','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--browser',action='store_true');a=p.parse_args()
    dll=a.dll.resolve(strict=True);frontend=a.frontend.resolve(strict=True);out=a.output.resolve()
    assert out.is_relative_to((ROOT/'.local').resolve()) and not out.exists()
    out.mkdir(parents=True);protect_directory(out)
    report=dict(result='FAIL',vmAccessed=False,qaAccessed=False,serverSha256=hashlib.sha256(dll.read_bytes()).hexdigest(),frontendSha256=hashlib.sha256((frontend/'app.js').read_bytes()).hexdigest())
    lab=Lab('inventory-json-export');start=time.monotonic()
    try:
        with lab:
            db=lab.create_database('inventory-json-export');ids,password=fixture(lab,db,dll)
            house=lab.sql(db,'SELECT id FROM systemhaus')
            ids.update({k:str(uuid.uuid4()) for k in ('site','building','room')})
            lab.sql(db,f"BEGIN; INSERT INTO inventory_site(id,systemhaus_id,customer_id,name) VALUES('{ids['site']}','{house}','{ids['customer']}','Synthetic Ω <img> site'); INSERT INTO inventory_building(id,systemhaus_id,customer_id,site_id,name) VALUES('{ids['building']}','{house}','{ids['customer']}','{ids['site']}','Building'); INSERT INTO inventory_room(id,systemhaus_id,customer_id,building_id,name) VALUES('{ids['room']}','{house}','{ids['customer']}','{ids['building']}','Room'); UPDATE inventory_rack SET room_id='{ids['room']}' WHERE id='{ids['mixedRack']}'; COMMIT;")
            lab.grant_runtime(db);server=lab.start_server(db,dll=dll,frontend=frontend);session=BatchSession(server,ids,password)
            parent=session.send(dict(profileKey='shelf-2u',profileVersion='hw-reference-v1',rackId=ids['mixedRack'],name='Shelf')).json()['result']['resourceId']
            session.send(dict(profileKey='desktop-firewall-6',profileVersion='hw-reference-v1',rackId=ids['mixedRack'],mountParentId=parent,mountSlotKey='main',name='Mounted Ω <img> firewall'))
            session.send(dict(profileKey='selected-apc-ar3100',profileVersion='selected506l-20261101-v1',roomId=ids['room'],name='Empty physical enclosure'),kind='rack.createHardware')
            expected=ordered(session.project());route=f"/api/v1/customers/{ids['customer']}/exports/inventory-json"
            def generate(client=session.client,key=None,revision=None,body=BODY,extra=None):
                actor=client.request('GET','/api/v1/me').json()['user']['id']
                headers={'X-RackClick-Actor':actor,'If-Match':f'"{session.revision if revision is None else revision}"','Idempotency-Key':key or str(uuid.uuid4())}
                headers.update(extra or {})
                return client.request('POST',route,body,headers)
            def durable():
                return lab.sql(db,"SELECT encode(sha256(convert_to(json_build_array((SELECT jsonb_agg(to_jsonb(t) ORDER BY id) FROM audit_event t),(SELECT jsonb_agg(to_jsonb(t) ORDER BY request_id) FROM operation t))::text,'UTF8')),'hex')")
            key=str(uuid.uuid4());response=generate(key=key);assert response.status==200,response.body
            receipt=response.json();archive=receipt['archive'];content=base64.b64decode(archive['contentBase64'],validate=True)
            assert hashlib.sha256(content).hexdigest()==archive['sha256'] and len(content)==archive['byteLength']<=4194304 and not content.startswith(b'\xef\xbb\xbf')
            document=json.loads(content);assert set(document)=={'formatVersion','kind','scope','customerId','revision','inventory'}
            assert (document['formatVersion'],document['kind'],document['scope'],document['customerId'],document['revision'])==(1,'RackClickInventory','customer',ids['customer'],session.revision)
            assert set(document['inventory'])==set(COLLECTIONS)
            assert document['inventory']=={k:session.project()[k] for k in COLLECTIONS}
            assert archive['rowCount']==sum(len(document['inventory'][k]) for k in COLLECTIONS)
            assert ordered(session.project())==expected
            audit=json.loads(lab.sql(db,f"SELECT after_json FROM audit_event WHERE request_id='{key}'"));assert 'contentBase64' not in audit and 'inventory' not in audit and audit['sourceRevision']==session.revision
            assert archive['filename']==f"rackclick-inventory-{ids['customer']}-r{session.revision}.json"
            before=durable();assert generate(key=key).json()==receipt and durable()==before
            status=session.client.request('GET',route+'/operations/'+key);assert status.status==200 and status.json()['operation']==receipt
            for body in ({},{'formatVersion':2,'scope':'customer'},{'formatVersion':1,'scope':'rack'},{**BODY,'includeUsers':True}):
                before=durable();assert generate(body=body).status==422 and durable()==before
            for extra,wanted in [({'X-RackClick-CSRF':'wrong'},403),({'Origin':'https://foreign.invalid'},403),({'X-RackClick-Actor':str(uuid.uuid4())},409)]:
                before=durable();assert generate(extra=extra).status==wanted and durable()==before
            reader=Client(server);assert reader.login('hardware-reader',password).status==200
            before=durable();assert generate(client=reader).status==403;assert reader.request('GET',route+'/operations/'+key).status==403;assert durable()==before
            assert reader.request('GET',f'/api/v1/customers/{uuid.uuid4()}/exports/inventory-json/operations/{key}').status==404
            # The generic recovery route cannot bypass the export capability.
            assert session.client.request('GET',session.route+'/operations/'+key).status==404
            old_revision=session.revision;session.send({'name':'Later source revision'},kind='site.create');assert generate(key=key,revision=old_revision).json()==receipt
            assert generate(revision=old_revision).status==412
            concurrent_key=str(uuid.uuid4())
            with ThreadPoolExecutor(2) as pool:
                results=list(pool.map(lambda _:generate(key=concurrent_key),range(2)))
            assert all(x.status==200 for x in results) and results[0].json()==results[1].json()
            assert lab.sql(db,f"SELECT count(*) FROM audit_event WHERE request_id='{concurrent_key}'")=='1'
            # Runtime still cannot mutate the catalogue; no reports-only permission is silently inferred.
            lab.sql(db,f"INSERT INTO permission_grant(id,systemhaus_id,user_group_id,capability,customer_id) VALUES(gen_random_uuid(),'{house}','{ids['readGroup']}','reports.export','{ids['customer']}')")
            reader_key=str(uuid.uuid4());assert generate(client=reader,key=reader_key).status==200
            lab.sql(db,f"DELETE FROM permission_grant WHERE user_group_id='{ids['readGroup']}' AND capability='reports.export'")
            before=durable();assert reader.request('GET',route+'/operations/'+reader_key).status==403;assert durable()==before
            lab.sql(db,"CREATE FUNCTION json_export_fail_audit() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF NEW.action='inventory.json.export' THEN RAISE EXCEPTION 'synthetic audit failure'; END IF; RETURN NEW; END $$; CREATE TRIGGER json_export_fail_audit BEFORE INSERT ON audit_event FOR EACH ROW EXECUTE FUNCTION json_export_fail_audit()")
            try:
                before=durable();assert generate().status>=500 and durable()==before
            finally:lab.sql(db,'DROP TRIGGER json_export_fail_audit ON audit_event; DROP FUNCTION json_export_fail_audit()')
            lab.sql(db,f"UPDATE inventory_port SET label=repeat('Ω',2200000) WHERE id='{ids['legacyPort']}'")
            try:
                before=durable();large=generate();assert large.status==422 and large.json()['error']=='report_too_large' and durable()==before
            finally:lab.sql(db,f"UPDATE inventory_port SET label='' WHERE id='{ids['legacyPort']}'")
            if a.browser:
                env=lab.environment();env.update(RACKCLICK_TEST_ORIGIN=server.origin,RACKCLICK_TEST_USERNAME='hardware-admin',RACKCLICK_TEST_PASSWORD=password,RACKCLICK_TEST_OUTPUT=str(out),RACKCLICK_FIXTURE=json.dumps(ids))
                with (out/'browser-private.log').open('wb') as log:
                    done=subprocess.run([str(toolchain()['node']),str(ROOT/'development/frontend/tests/browser-inventory-json-export.mjs')],cwd=ROOT/'development/frontend',env=env,stdout=log,stderr=log,timeout=240,creationflags=NO_WINDOW)
                assert done.returncode==0,'Browser runner failed; private log retained'
            server.close();server=lab.start_server(db,dll=dll,frontend=frontend);second=Client(server);assert second.login('hardware-admin',password).status==200
            assert second.request('GET',route+'/operations/'+key).json()['operation']==receipt
            report.update(result='PASS',schema=lab.sql(db,'SELECT max(version) FROM schema_migration'),format='RackClickInventory-v1',inventoryCollections=8,
                sourceSnapshotExact=True,hardwareMountsAndMetadataPreserved=True,securityCollectionsExcluded=True,serverConfirmedIdempotentAndConcurrent=True,
                historicalReceiptAfterSourceChangeAndRestart=True,permissionRevocationAndGenericBypassRejected=True,auditRollback=True,oversizeRejectedWithoutTruncation=True,
                csrfOriginActorAndRevisionGuards=True,browserExecuted=a.browser,postgresql=lab.sql('postgres','SHOW server_version'))
    except BaseException as error:
        report['failureType']=type(error).__name__; (out/'failure-private.log').write_text(traceback.format_exc(),encoding='utf-8')
    finally:
        report.update(labStopped=not lab.running,serversStopped=all(s.process.poll() is not None for s in lab.servers),elapsedSeconds=round(time.monotonic()-start,3))
        (out/'RESULTADOS.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
    return 0 if report['result']=='PASS' else 1


if __name__=='__main__':raise SystemExit(main())
