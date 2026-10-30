"""One new Windows/PostgreSQL/Edge category-palette fixture, with explicit frozen artifacts."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'development/server/tests'))
sys.path.insert(0, str(ROOT / 'tools/windows'))
from pg_support import Lab, Client, toolchain
from windows_job import run_isolated
from test_inventory_movement_gui import fixture, durable, tree


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_bytes())
    assert manifest['schema'] == 13
    dll, frontend = ROOT / manifest['serverDll'], ROOT / manifest['frontend']
    original = dict(server=tree(dll.parent), frontend=tree(frontend))
    assert original == manifest['distributions']
    paths = [Path(__file__), Path(__file__).with_name('pg_support.py'),
             Path(__file__).with_name('test_inventory_movement_gui.py'), ROOT / 'tools/windows/windows_job.py',
             ROOT / 'development/frontend/tests/browser-quince-support.mjs',
             ROOT / 'development/frontend/tests/browser-user-category-colors1089.mjs']
    sources = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    args.output.mkdir(parents=True, exist_ok=False)
    lab = Lab('category-colors1089gui')
    started = time.monotonic()
    report = dict(utc=datetime.now(timezone.utc).isoformat(), platform=platform.platform(), result='FAIL',
                  sources=sources, realQaAccessed=False, historicalResultsReused=False,
                  manifestSha256=hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
                  fixtureCreatedBy='New synthetic SQL fixture; writes under test use real HTTP/Edge.')
    try:
        with lab:
            db = lab.create_database('categorycolorsgui')
            ids, password = fixture(lab, db, dll)
            ids['none'] = str(uuid.uuid4())
            lab.sql(db, f"INSERT INTO app_user(id,systemhaus_id,username,password_hash) SELECT '{ids['none']}',systemhaus_id,'category-none',password_hash FROM app_user WHERE username='move-admin';", sensitive=True)
            # Synthetic persisted preset keys determine categories; translated labels deliberately disagree.
            lab.sql(db, f"UPDATE inventory_port SET color=NULL,poe=false,watts=NULL,status='free';")
            for key,preset,label in [('a','pp24','Switch traducido'),('b','sw24','Servidor traducido'),('c','srv1u','Patch Panel')]:
                props=json.dumps({'catalog':{'presetKey':preset},'preset':label})
                lab.sql(db,f"UPDATE inventory_device SET properties=properties||'{props}'::jsonb WHERE id='{ids[key]}';")
                for number in [3,4]:
                    ids['p'+key+str(number)]=str(uuid.uuid4())
                    lab.sql(db,f"INSERT INTO inventory_port(id,systemhaus_id,customer_id,device_id,group_id,type,gn,sort_order,label,status,poe,watts,color,face,properties) SELECT '{ids['p'+key+str(number)]}',systemhaus_id,customer_id,device_id,group_id,type,{number},{number-1},'Extra {key}{number}','free',false,NULL,NULL,'front','{{}}'::jsonb FROM inventory_port WHERE id='{ids['p'+key]}';")
            assert lab.sql(db,'SELECT max(version) FROM schema_migration')=='13'
            lab.grant_runtime(db)
            before = durable(lab, db)
            revisions = lab.sql(db, "SELECT jsonb_build_object('house',(SELECT revision FROM systemhaus),'customers',(SELECT jsonb_object_agg(id,revision) FROM customer))")
            server = lab.start_server(db, dll=dll, frontend=frontend)
            env = lab.environment()
            env.update(RACKCLICK_TEST_ORIGIN=server.origin, RACKCLICK_TEST_USERNAME='move-reader',
                       RACKCLICK_TEST_PASSWORD=password, RACKCLICK_TEST_OUTPUT=str(args.output.resolve()),
                       RACKCLICK_FIXTURE=json.dumps(ids))
            browser_started = time.monotonic()
            with (args.output / 'browser-windows.log').open('xb') as log:
                done = run_isolated([str(toolchain()['node']), str(ROOT / 'development/frontend/tests/browser-user-category-colors1089.mjs')],
                    env=env, cwd=ROOT / 'development/frontend', stdout=log, stderr=log, timeout=240)
            report.update(browserExitCode=done.returncode, browserSeconds=round(time.monotonic()-browser_started,3))
            if done.returncode:
                raise RuntimeError('Browser failed; sanitized evidence preserved')
            expected = json.loads((args.output / 'expected-colors.json').read_bytes())
            after=durable(lab,db)
            assert all(after[t]==before[t] for t in before if t not in ['inventory_connection','inventory_connection_endpoint'])
            assert [r for r in after['inventory_connection'] if r['id']==ids['cable']]==before['inventory_connection']
            assert len(after['inventory_connection'])==5 and len(after['inventory_connection_endpoint'])==10
            assert lab.sql(db,'SELECT count(*) FROM operation')=='3'
            assert lab.sql(db,'SELECT count(*) FROM user_port_colors')=='0'
            assert lab.sql(db,'SELECT count(*) FROM user_port_color_operation')=='0'
            journals=lab.sql(db,'SELECT count(*) FROM user_category_color_operation')
            audits=lab.sql(db,"SELECT count(*) FROM audit_event WHERE action LIKE 'user.categoryColors.%'")
            assert journals==audits and int(journals)>=6
            rows = lab.sql(db, 'SELECT jsonb_agg(to_jsonb(t) ORDER BY owner_id) FROM user_category_colors t')
            server.close()
            restarted = lab.start_server(db, dll=dll, frontend=frontend)
            for username, key in [('move-reader','reader'),('category-none','none'),('move-admin','admin')]:
                client = Client(restarted)
                assert client.login(username,password).status == 200
                response = client.request('GET','/api/v1/me/category-colors')
                assert response.status == 200 and response.json() == expected[key]
                assert response.headers.get('etag') == f'"category-colors-{expected[key]["revision"]}"'
            assert lab.sql(db, 'SELECT jsonb_agg(to_jsonb(t) ORDER BY owner_id) FROM user_category_colors t') == rows
            assert durable(lab, db) == after
            report.update(result='PASS', inventoryNonConnectionTablesExact=True, originalCableExact=True, guiConnectionCount=5, guiCreateCommands=3, portPalette12Untouched=True,
                          journalAndAuditCount=int(journals), serverRestartPersistence=True, schema=13,
                          postgresql=lab.sql('postgres','SHOW server_version'), screenReaderVoiceTested=False)
    except Exception as error:
        report.update(failureType=type(error).__name__, failure=str(error))
    finally:
        report.update(seconds=round(time.monotonic()-started,3), labStopped=not lab.running,
                      serversStopped=all(s.process.poll() is not None for s in lab.servers),
                      artifactsUnchanged=original == dict(server=tree(dll.parent), frontend=tree(frontend)),
                      sourcesUnchanged=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in sources.items()))
        (args.output/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({k:v for k,v in report.items() if k!='sources'},indent=2))
    return 0 if report['result']=='PASS' and all(report[k] for k in ['labStopped','serversStopped','artifactsUnchanged','sourcesUnchanged']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
