"""Three rename-only PostgreSQL focuses; frozen artifacts and fresh Windows labs."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import time
import unittest

from pg_support import Client, Lab, WORKSPACE, NO_WINDOW, literal
from test_postgres import EvidenceResult, Tee
from test_private_device_templates import PrivateDeviceTemplatesPostgres, MAX_REVISION, distribution, uid


class PrivateTemplateRenamePostgres(PrivateDeviceTemplatesPostgres):
    def rename_intent(self, template, name):
        return {'type':'rename','templateId':template,'name':name}

    def simple_template(self, client=None, name='Original'):
        _,_,_,rack=self.hierarchy()
        device,_,_=self.device('Source',rack=rack['id'])
        result=self.capture(device,name=name,client=client)
        return device,result['result']['templateId']

    def immutable(self, template):
        # Includes UUID, owner, created_at, active, exact TEXT, version and hash.
        return self.lab.sql(self.db,f"SELECT (to_jsonb(t)-'name')::text FROM user_device_template t WHERE id='{template}'")

    def once(self, key, action='rename'):
        self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM user_device_template_operation WHERE request_id='{key}'"),'1')
        self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM audit_event WHERE request_id='{key}' AND action='user.deviceTemplate.{action}'"),'1')

    def test_01_unicode_noop_exact_immutability_source_deleted_and_restart(self):
        device,_,_,_,_,_,_=self.rich(); capture=self.capture(device); template=capture['result']['templateId']
        saved=self.immutable(template); raw=self.detail(template)[2]; inventory=self.snapshot()
        house=self.lab.sql(self.db,'SELECT revision FROM systemhaus')
        for index,name in enumerate([' \u00a0Café 同名 🧰\u00a0 ','e\u0301','é','😀'*100]):
            normalized=name.strip(); revision=self.templates()['revision']; key=uid()
            receipt=self.change(self.rename_intent(template,name),revision=revision,key=key).json()
            self.assertEqual((receipt['revision'],receipt['result']['type'],receipt['result']['name'],receipt['result']['active'],receipt['result']['changed']),
                (revision+1,'rename',normalized,True,True))
            self.assertEqual(receipt['result']['definitionSha256'],capture['result']['definitionSha256'])
            self.assertEqual(self.detail(template)[0]['template']['name'],normalized)
            self.assertEqual(self.detail(template)[2],raw); self.assertEqual(self.immutable(template),saved); self.once(key)
            self.assertEqual(self.snapshot(),inventory); self.assertEqual(self.poll(inventory['revision'])['events'],[])
            self.assertEqual(self.lab.sql(self.db,'SELECT revision FROM systemhaus'),house)
            noopkey=uid(); noop=self.change(self.rename_intent(template,' '+normalized+' '),key=noopkey).json()
            self.assertFalse(noop['result']['changed']); self.assertEqual(noop['revision'],revision+1); self.once(noopkey)
        # Duplicate display names remain legal; UUIDs, not names, identify templates.
        duplicate=self.capture(device,name='😀'*100)['result']['templateId']; self.assertNotEqual(duplicate,template)
        self.assertEqual([t['name'] for t in self.templates()['templates']],['😀'*100]*2)
        intent=self.rename_intent(template,'Renamed after source deletion'); preview=self.preview('device.delete',{'id':device['id']})
        self.command('device.delete',{'id':device['id'],'confirmationToken':preview['confirmationToken']})
        inventory=self.snapshot(); self.assertFalse(any(d['id']==device['id'] for d in inventory['devices']))
        key=uid(); receipt=self.change(intent,key=key).json(); self.assertEqual(self.immutable(template),saved)
        self.assertEqual(self.snapshot(),inventory); self.assertEqual(self.poll(inventory['revision'])['events'],[])
        self.server.close(); self.server=self.lab.start_server(self.db,dll=self.dll,frontend=self.frontend)
        self.admin.server=self.server; fresh=Client(self.server); fresh.actor_id=self.admin_id
        self.expect(fresh.login('qa-inventory-admin',self.password),200)
        self.assertEqual(self.detail(template,client=fresh)[2],raw)
        self.assertEqual(self.detail(template,client=fresh)[0]['template']['name'],intent['name'])
        self.assertEqual(self.outcome(key,client=fresh).json()['operation'],receipt)
        self.assertEqual(self.immutable(template),saved); self.once(key)
        spec=self.expect(fresh.request('GET','/api/v1/openapi.json'),200).json()['components']['schemas']
        self.assertEqual(set(spec['PrivateTemplateRename']['properties']),{'type','templateId','name'})
        self.assertEqual(set(spec['PrivateTemplateRename']['required']),{'type','templateId','name'})
        self.assertFalse(spec['PrivateTemplateRename']['additionalProperties'])
        self.assertIn({'$ref':'#/components/schemas/PrivateTemplateRename'},spec['PrivateTemplateIntent']['oneOf'])
        self.assertEqual(spec['PrivateTemplateChange']['properties']['type']['enum'],['capture','deactivate','rename','create'])

    def test_02_closed_validation_scope_csrf_wait_revocation_revision_and_inactive(self):
        device,template=self.simple_template(); intent=self.rename_intent(template,'Changed')
        reader,_,_=self.add_user('rename-reader',['inventory.read'],self.customer_id)
        other,_,_=self.add_user('rename-other',['inventory.read','inventory.edit'],self.customer_id)
        no_read,_,_=self.add_user('rename-no-read',['inventory.edit'],self.customer_id)
        self.change(intent,client=reader,revision=0,status=403)
        self.change(intent,client=other,revision=0,status=404); self.change(intent,client=no_read,revision=0,status=404)
        self.change(intent,customer=uid(),revision=1,status=404)
        self.change(intent,revision=1,status=403,headers={'X-RackClick-CSRF':'invalid'})
        self.change(intent,revision=1,status=403,headers={'Origin':'https://foreign.invalid'})
        self.change(intent,revision=1,status=409,headers={'X-RackClick-Actor':other.actor_id})
        invalid=[{**intent,'sourceRevision':1},{**intent,'definitionSha256':'0'*64},{**intent,'ownerId':self.admin_id},
            {**intent,'deviceId':device['id']},{'type':'rename','templateId':template},
            {**intent,'name':None},{**intent,'name':True},{**intent,'templateId':'not-a-uuid'},
            *[{**intent,'name':name} for name in ['😀'*101,'','   ','bad\x00','bad\nname','bad\ud800']]]
        before=self.durable()
        for body in invalid: self.change(body,revision=1,status=422)
        duplicate=json.dumps(intent)[:-1]+',"name":"duplicate"}'
        self.expect(self.admin.request('POST',self.path(),duplicate,{'Content-Type':'application/json','If-Match':'"templates-1"',
            'Idempotency-Key':uid(),'X-RackClick-Actor':self.admin_id}),422)
        self.expect(self.change(intent,revision=0,status=412),412,'revision_conflict')
        self.assertEqual(before,self.durable())
        # Every pending request first owns a usable active template; denial discriminates reauthorization.
        for mode in ['edit','read','session']:
            actor,group,_=self.add_user('rename-wait-'+mode,['inventory.read','inventory.edit'],self.customer_id)
            own=self.capture(device,client=actor)['result']['templateId']; key=uid(); pending_intent=self.rename_intent(own,'Must never persist')
            saved=self.immutable(own); label='rename_wait_'+uid().replace('-','')
            lockkey=f'RackClick/private-device-templates/{self.house_id}/{actor.actor_id}'
            # Authorize holds FOR SHARE on this row: expiry must occur naturally,
            # not via an UPDATE that would itself wait until the request commits.
            if mode=='session':
                self.lab.sql(self.db,f"UPDATE app_session SET expires_at=clock_timestamp()+interval '2 seconds' WHERE user_id='{actor.actor_id}'")
            with ThreadPoolExecutor(2) as pool:
                holder=pool.submit(self.lab.sql,self.db,f"SET application_name='{label}'; BEGIN; SELECT pg_advisory_xact_lock(hashtextextended('{lockkey}',0)); SELECT pg_sleep(3); COMMIT;")
                self.wait_for(f"SELECT count(*) FROM pg_stat_activity WHERE application_name='{label}' AND wait_event='PgSleep'")
                pending=pool.submit(actor.request,'POST',self.path(),pending_intent,{'If-Match':'"templates-1"',
                    'Idempotency-Key':key,'X-RackClick-Actor':actor.actor_id})
                self.wait_for(f"SELECT count(*) FROM pg_stat_activity WHERE datname='{self.db.name}' AND usename='{self.db.runtime}' AND cardinality(pg_blocking_pids(pid))>0")
                if mode!='session':
                    capability='inventory.edit' if mode=='edit' else 'inventory.read'
                    self.lab.sql(self.db,f"DELETE FROM permission_grant WHERE user_group_id='{group}' AND capability='{capability}'")
                self.expect(pending.result(timeout=15),{'edit':403,'read':404,'session':401}[mode]); holder.result(timeout=10)
            self.assertEqual(self.immutable(own),saved)
            self.assertEqual(self.lab.sql(self.db,f"SELECT name FROM user_device_template WHERE id='{own}'"),'Plantilla Café 同名')
            self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM user_device_template_operation WHERE request_id='{key}'"),'0')
            self.assertEqual(self.lab.sql(self.db,f"SELECT count(*) FROM audit_event WHERE request_id='{key}'"),'0')
        inactive=self.capture(device,name='Inactive')['result']['templateId']; self.change({'type':'deactivate','templateId':inactive})
        before=self.durable(); self.expect(self.change(self.rename_intent(inactive,'Inactive'),status=409),409,'template_inactive')
        self.assertEqual(before,self.durable())
        self.lab.sql(self.db,f"UPDATE user_device_templates SET revision={MAX_REVISION} WHERE owner_id='{self.admin_id}'")
        no_op=self.change(self.rename_intent(template,'Original'),revision=MAX_REVISION).json()
        self.assertFalse(no_op['result']['changed']); self.assertEqual(no_op['revision'],MAX_REVISION); self.once(no_op['requestId'])
        before=self.durable()
        self.expect(self.change(intent,revision=MAX_REVISION,status=409),409,'templates_revision_exhausted'); self.assertEqual(before,self.durable())

    def test_03_lost_reply_replay_cancel_digest_concurrency_rollback_and_audit(self):
        _,template=self.simple_template(); intent=self.rename_intent(template,'Historic name'); key=uid(); revision=1
        # Pretend the body was lost: recover the committed receipt via a second session.
        self.expect(self.admin.request('POST',self.path(),intent,{'If-Match':'"templates-1"','Idempotency-Key':key,'X-RackClick-Actor':self.admin_id}),200)
        second=Client(self.server); second.actor_id=self.admin_id; self.expect(second.login('qa-inventory-admin',self.password),200)
        first=self.outcome(key,client=second).json()['operation']; self.assertEqual(first['result']['name'],'Historic name')
        self.assertEqual(self.change(intent,revision=revision,key=key,client=second).json(),first); self.once(key)
        self.assertEqual(self.change({**intent,'name':'  Historic name  '},revision=revision,key=key,client=second).json(),first)
        self.change(self.rename_intent(template,'Current name'))
        self.change({'type':'deactivate','templateId':template})
        self.assertEqual(self.change(intent,revision=revision,key=key).json(),first)
        self.assertEqual(self.cancel_template(key,intent,revision=revision).json()['operation'],first); self.once(key)
        for body,expected in [({**intent,'name':'Changed digest'},revision),(intent,revision+1),({'type':'deactivate','templateId':template},revision)]:
            self.expect(self.change(body,revision=expected,key=key,status=409),409,'request_id_reused')
        context=self.customer('Other rename context')['id']
        self.expect(self.change(intent,revision=revision,key=key,customer=context,status=409),409,'request_id_reused')
        self.outcome(key,customer=context,status=404)
        cancelkey=uid(); impossible=self.rename_intent(uid(),'Unsent rename')
        terminal=self.cancel_template(cancelkey,impossible,revision=0).json(); self.assertEqual(terminal['state'],'cancelled')
        self.assertEqual(self.cancel_template(cancelkey,impossible,revision=0).json(),terminal)
        self.expect(self.change(impossible,revision=0,key=cancelkey,status=409),409,'operation_cancelled'); self.once(cancelkey,'rename.cancel')
        _,active=self.simple_template(name='Concurrent'); immutable=self.immutable(active)
        revision=self.templates()['revision']; samekey=uid(); body=self.rename_intent(active,'One rename')
        with ThreadPoolExecutor(2) as pool:
            results=list(pool.map(lambda _:self.change(body,revision=revision,key=samekey).json(),range(2)))
        self.assertEqual(results[0],results[1]); self.assertEqual(self.templates()['revision'],revision+1); self.once(samekey)
        revision=self.templates()['revision']
        with ThreadPoolExecutor(2) as pool:
            results=list(pool.map(lambda name:self.admin.request('POST',self.path(),self.rename_intent(active,name),
                {'If-Match':f'"templates-{revision}"','Idempotency-Key':uid(),'X-RackClick-Actor':self.admin_id}),['Left','Right']))
        self.assertEqual(sorted(r.status for r in results),[200,412]); self.assertEqual(self.templates()['revision'],revision+1)
        for table in ['audit_event','user_device_template_operation']:
            self.lab.sql(self.db,f"CREATE FUNCTION rename_failure() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'isolated rename rollback' USING ERRCODE='23514'; END $$; CREATE TRIGGER rename_fail BEFORE INSERT ON {table} FOR EACH ROW EXECUTE FUNCTION rename_failure();")
            before=self.durable(); failkey=uid()
            try:
                self.expect(self.change(self.rename_intent(active,'Rollback both metadata and revision'),key=failkey,status=409),409,'templates_conflict')
                self.assertEqual(before,self.durable())
            finally: self.lab.sql(self.db,f'DROP TRIGGER rename_fail ON {table}; DROP FUNCTION rename_failure();')
        self.assertEqual(self.immutable(active),immutable)
        revision=self.templates()['revision']; race=uid(); body=self.rename_intent(active,'Commit versus fence')
        with ThreadPoolExecutor(2) as pool:
            apply=pool.submit(self.admin.request,'POST',self.path(),body,{'If-Match':f'"templates-{revision}"','Idempotency-Key':race,'X-RackClick-Actor':self.admin_id})
            cancel=pool.submit(self.cancel_template,race,body,revision)
            applied,terminal=apply.result(timeout=15),cancel.result(timeout=15).json()
        if terminal['state']=='cancelled': self.expect(applied,409,'operation_cancelled'); self.once(race,'rename.cancel')
        else: self.expect(applied,200); self.assertEqual(terminal['operation'],applied.json()); self.once(race)
        self.assertEqual(self.immutable(active),immutable)
        event=json.loads(self.lab.sql(self.db,f"SELECT row_to_json(t) FROM audit_event t WHERE request_id='{samekey}'"))
        self.assertEqual((event['actor_id'],event['resource_id'],event['action']),(self.admin_id,active,'user.deviceTemplate.rename'))
        self.assertEqual(event['before_json']['template']['name'],'Concurrent'); self.assertEqual(event['after_json']['template']['name'],'One rename')
        for value in ['definitionBase64','definition_json','portGroups','SOURCE-PRIVATE']:
            self.assertNotIn(value,json.dumps(event))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['dll','frontend','evidence']: parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--case',action='append',required=True); args=parser.parse_args()
    available=[n for n in PrivateTemplateRenamePostgres.__dict__ if n.startswith('test_')]
    if set(args.case)-set(available): raise ValueError('Unknown rename focus')
    names=[n for n in available if n in args.case]
    args.dll=args.dll.resolve(); args.frontend=args.frontend.resolve()
    if not args.dll.is_file() or not args.frontend.is_dir(): raise ValueError('Explicit frozen artifacts required')
    args.evidence.mkdir(parents=True,exist_ok=False)
    files=[p for p in (WORKSPACE/'development/server/src').rglob('*.cs') if 'obj' not in p.parts and 'bin' not in p.parts]
    files+=list((WORKSPACE/'development/server/database').glob('*.sql'))+[Path(__file__).resolve(),WORKSPACE/'development/catalog/rc9-catalog.json']
    files+=[WORKSPACE/'development/server/tests'/n for n in ['pg_support.py','test_postgres.py','test_inventory_postgres.py','test_inventory_changes.py','test_inventory_read_views.py','test_private_device_templates.py']]
    def sources(): return {p.relative_to(WORKSPACE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    original=sources(); server=distribution(args.dll.parent); frontend=distribution(args.frontend)
    report={'utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'python':platform.python_version(),
        'serverPath':str(args.dll.parent),'frontendPath':str(args.frontend),'serverHashes':server,'frontendHashes':frontend,
        'sourceHashes':original,'selectedCases':names,'schemaVersion':9,'actualQaOpened':False,'historicalResultsReused':False}
    (args.evidence/'inputs-before.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    lab=Lab('private-template-rename'); PrivateTemplateRenamePostgres.lab=lab
    PrivateTemplateRenamePostgres.dll,PrivateTemplateRenamePostgres.frontend=args.dll,args.frontend
    report['versions']={name:subprocess.run([str(path),'--version'],capture_output=True,text=True,check=True,creationflags=NO_WINDOW).stdout.strip()
        for name,path in [('dotnet',lab.dotnet),('postgres',lab.pg_bin/'postgres.exe')]}
    started=time.monotonic()
    with lab,(args.evidence/'tests.log').open('w',encoding='utf-8') as output:
        result=unittest.TextTestRunner(stream=Tee(sys.stdout,output),verbosity=2,resultclass=EvidenceResult).run(unittest.TestSuite(PrivateTemplateRenamePostgres(n) for n in names))
        report.update(testsRun=result.testsRun,cases=result.records,successful=result.wasSuccessful())
    report.update(elapsedSeconds=round(time.monotonic()-started,3),labStopped=not lab.running,
        serversStopped=all(s.process.poll() is not None for s in lab.servers),sourcesUnchanged=original==sources(),
        serverUnchanged=server==distribution(args.dll.parent),frontendUnchanged=frontend==distribution(args.frontend))
    (args.evidence/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return 0 if all(report[k] for k in ['successful','labStopped','serversStopped','sourcesUnchanged','serverUnchanged','frontendUnchanged']) else 1


if __name__=='__main__': sys.exit(main())
