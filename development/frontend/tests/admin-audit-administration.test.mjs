import test from 'node:test';
import assert from 'node:assert/strict';
import {RackClickApi,ApiError} from '../src/api.ts';
import {readAdministrativeAuditDetail,isAdministrativeAuditAction} from '../src/admin-audit.ts';
const actor='12345678-1234-1234-1234-123456789abc',resource='bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',id='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',other='cccccccc-cccc-4ccc-8ccc-cccccccccccc',zero='00000000-0000-0000-0000-000000000000';
const event=action=>({id,occurredAt:'2026-10-16T12:34:56.123456Z',actor:{id:actor,userName:'Prior actor'},requestId:other,action,resourceId:resource});
const field=(field,type,before,after)=>({field,type,before,after});
function data(action='user.state.set'){
 const item=event(action),f=[];const add=(...args)=>f.push(field(...args));
 if(action.endsWith('.cancel')){
  if(action==='user.session.revoke.cancel'){add('userId','uuid',actor,null);add('sessionId','uuid',resource,null);}
  add('requestId','uuid',null,other);add('state','state',null,'cancelled');
 }else if(action==='user.create'||action==='user.state.set'||action==='user.password.reset'){
  const create=action==='user.create';add('userId','uuid',create?null:resource,resource);add('userName','userName',create?null:'\ufeffLegacy Ä <img> 😀','\ufeffLegacy Ä <img> 😀');add('active','boolean',create?null:'true',action==='user.state.set'?'false':'true');if(action==='user.password.reset')add('passwordReset','boolean',null,'true');
 }else if(action.endsWith('.create')){
  add('groupId','uuid',null,resource);add('name','name',null,'Grupo e\u0301 <img> 😀');add('groupKind','groupKind',null,action==='userGroup.create'?'userGroup':'customerGroup');
 }else if(action==='user.session.revoke'){
  add('userId','uuid',actor,actor);add('sessionId','uuid',resource,resource);add('revoked','boolean',null,'true');add('wasCurrent','boolean',null,'true');
 }else{
  add('groupId','uuid',resource,resource);
  if(action==='userGroup.grant.set'){add('grantId','uuid',other,other);add('capability','capability','inventory.read','inventory.read');add('scope','scope','systemhaus','systemhaus');add('targetId','uuid',null,null);}
  else add(action==='userGroup.member.set'?'userId':'customerId','uuid',other,other);
  add('assigned','boolean','false','true');
 }
 return {revision:7,event:{...item,actor:{id:actor,userName:'Current actor'}},detail:{status:'available',fields:f}};
}
const actions=['user.create','userGroup.create','customerGroup.create','userGroup.member.set','customerGroup.member.set','userGroup.grant.set','user.state.set','user.password.reset','user.session.revoke'];
const reply=(value,etag='"7"')=>new Response(JSON.stringify(value),{headers:{ETag:etag}});
function api(fetcher){const a=new RackClickApi(fetcher);a.actorId=actor;return a;}
const from=(value,etag)=>api(async()=>reply(value,etag));
for(const action of actions.flatMap(a=>[a,a+'.cancel']))test('campos administrativos válidos: '+action,async()=>{assert.equal(isAdministrativeAuditAction(action),true);const d=data(action);assert.deepEqual(await readAdministrativeAuditDetail(from(d),event(action)),d);});
test('GET exacto sin cuerpo/caché/CSRF; el nombre de actor puede cambiar',async()=>{
 const d=data();const a=api(async(path,init)=>{assert.equal(path,'/api/v1/admin/audit/'+id+'/administrative-detail');assert.equal(init.cache,'no-store');assert.equal(init.credentials,'same-origin');assert.equal(init.method,undefined);assert.equal(init.body,undefined);assert.equal(init.headers,undefined);return reply(d);});assert.deepEqual(await readAdministrativeAuditDetail(a,event('user.state.set')),d);
});
test('unavailable sin campos; no se reconstruye historia',async()=>{const d=data();d.detail={status:'unavailable',fields:[]};assert.deepEqual(await readAdministrativeAuditDetail(from(d),event('user.state.set')),d);});
test('100 runas, BOM y Unicode descompuesto se conservan literalmente',async()=>{for(const name of ['😀'.repeat(100),'e\u0301','\ufeff']){const d=data('user.create');d.detail.fields[1].after=name;assert.equal((await readAdministrativeAuditDetail(from(d),d.event)).detail.fields[1].after,name);}});
test('identidades admiten casing UUID; membresía sin cambio y ámbito de cliente válidos',async()=>{
 const d=data('userGroup.member.set');d.detail.fields[0].after=resource.toUpperCase();d.detail.fields[2].before='true';assert.deepEqual(await readAdministrativeAuditDetail(from(d),d.event),d);
 for(const scope of ['customer','customerGroup']){const g=data('userGroup.grant.set');g.detail.fields[3].before=g.detail.fields[3].after=scope;g.detail.fields[4].before=g.detail.fields[4].after=actor;assert.deepEqual(await readAdministrativeAuditDetail(from(g),g.event),g);}
});
const invalid={
 'top extra':d=>d.secret='synthetic','unsafe revision':d=>d.revision=Number.MAX_SAFE_INTEGER+1,'event extra':d=>d.event.raw_json={},'event ID':d=>d.event.id=other,'actor ID':d=>d.event.actor.id=other,'request ID':d=>d.event.requestId=actor,'resource ID':d=>d.event.resourceId=other,'timestamp precision':d=>d.event.occurredAt='2026-10-16T12:34:56.123457Z','action':d=>d.event.action='user.password.reset',
 'detail extra':d=>d.detail.raw_json={},'status':d=>d.detail.status='ready','unavailable with fields':d=>d.detail.status='unavailable','fields not array':d=>d.detail.fields={},'missing field':d=>d.detail.fields.pop(),'duplicate field':d=>d.detail.fields[1]=d.detail.fields[0],'order':d=>d.detail.fields.reverse(),'field extra':d=>d.detail.fields[0].secret='synthetic','type':d=>d.detail.fields[0].type='text','unknown field':d=>d.detail.fields[0].field='passwordHash',
 'zero UUID':d=>d.detail.fields[0].after=zero,'other subject':d=>d.detail.fields[0].after=other,'UUID shape':d=>d.detail.fields[0].after=resource.replaceAll('-',''),'boolean as boolean':d=>d.detail.fields[2].after=false,'boolean code':d=>d.detail.fields[2].after='False','state missing before':d=>d.detail.fields[2].before=null,'changed username':d=>d.detail.fields[1].after='Other','number username':d=>d.detail.fields[1].after=33,'leading whitespace':d=>d.detail.fields[1].before=d.detail.fields[1].after=' spaced','control':d=>d.detail.fields[1].before=d.detail.fields[1].after='bad\u0000','surrogate':d=>d.detail.fields[1].before=d.detail.fields[1].after='bad\ud800','101 runes':d=>d.detail.fields[1].before=d.detail.fields[1].after='😀'.repeat(101)
};
for(const [name,mutate]of Object.entries(invalid))test('rechaza respuesta administrativa: '+name,async()=>{const d=data();mutate(d);await assert.rejects(()=>readAdministrativeAuditDetail(from(d),event('user.state.set')),e=>e instanceof ApiError&&e.code==='response_invalid');});
for(const [action,mutate]of[
 ['user.create',d=>d.detail.fields[2].after='false'],['user.create',d=>d.detail.fields[0].before=resource],['userGroup.create',d=>d.detail.fields[2].after='customerGroup'],
 ['userGroup.member.set',d=>d.detail.fields[1].before=actor],['userGroup.grant.set',d=>d.detail.fields[2].after='unknown.capability'],['userGroup.grant.set',d=>d.detail.fields[4].after=actor],['userGroup.grant.set',d=>d.detail.fields[3].before=d.detail.fields[3].after='customer'],['userGroup.grant.set',d=>d.detail.fields[3].after='customerGroup'],
 ['user.password.reset',d=>d.detail.fields[3].after='false'],['user.password.reset',d=>d.detail.fields[2].after='false'],['user.session.revoke',d=>d.detail.fields[0].before=d.detail.fields[0].after=other],['user.session.revoke',d=>d.detail.fields[2].after='false'],['user.session.revoke',d=>d.detail.fields[3].before='true'],
 ['user.create.cancel',d=>d.detail.fields[0].after=actor],['userGroup.member.set.cancel',d=>d.detail.fields[1].after='committed'],['user.session.revoke.cancel',d=>d.detail.fields[1].before=other],['user.session.revoke.cancel',d=>d.detail.fields[0].after=actor]
])test('coherencia histórica: '+action+' '+mutate.toString(),async()=>{const d=data(action);mutate(d);await assert.rejects(()=>readAdministrativeAuditDetail(from(d),event(action)),e=>e.code==='response_invalid');});
test('actor o selección inválidos no hacen HTTP; nombres46 no se envían a ruta administrativa',async()=>{let requests=0;const a=api(async()=>{requests++;return reply(data());});a.actorId=other;await assert.rejects(()=>readAdministrativeAuditDetail(a,event('user.create'),actor),e=>e.code==='actor_changed');a.actorId=actor;for(const action of ['customer.create','systemhaus.rename','synthetic.cancel','toString']){assert.equal(isAdministrativeAuditAction(action),false);await assert.rejects(()=>readAdministrativeAuditDetail(a,event(action)),e=>e.code==='request_invalid');}assert.equal(requests,0);});
test('actor después de await y metadatos capturados antes de await',async()=>{
 const d=data(),selected=event('user.state.set');let release;const a=api(()=>new Promise(r=>release=r));const pending=readAdministrativeAuditDetail(a,selected);selected.id=other;selected.actor.id=other;release(reply(d));assert.deepEqual(await pending,d);
 let release2;const b=api(()=>new Promise(r=>release2=r));const stale=readAdministrativeAuditDetail(b,event('user.state.set'));b.actorId=other;release2(reply(d));await assert.rejects(()=>stale,e=>e.code==='actor_changed');
});
test('ETag incompatible y errores HTTP/red no ofrecen valores anteriores',async()=>{await assert.rejects(()=>readAdministrativeAuditDetail(from(data(),'"8"'),event('user.state.set')),e=>e.code==='response_invalid');for(const status of [401,403,404])await assert.rejects(()=>readAdministrativeAuditDetail(api(async()=>new Response('{"error":"synthetic"}',{status})),event('user.state.set')),e=>e.status===status);await assert.rejects(()=>readAdministrativeAuditDetail(api(async()=>{throw Error('offline');}),event('user.state.set')),e=>e.code==='network_unconfirmed');});
