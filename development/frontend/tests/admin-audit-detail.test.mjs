import test from 'node:test';
import assert from 'node:assert/strict';
import {RackClickApi} from '../src/api.ts';
import {readAuditDetail,readAuditPage} from '../src/admin-audit.ts';
const actor='12345678-1234-1234-1234-123456789abc',resource='bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',id='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',other='cccccccc-cccc-4ccc-8ccc-cccccccccccc',zero='00000000-0000-0000-0000-000000000000';
const event=()=>({id,occurredAt:'2026-10-16T12:34:56.123456Z',actor:{id:actor,userName:'Old actor'},requestId:actor,action:'customer.rename',resourceId:resource});
const data=()=>({revision:7,event:{...event(),actor:{id:actor,userName:'Current actor <img> Ä 😀'}},detail:{status:'available',revisionScope:'customer',customerId:resource,before:{name:'Antes e\u0301 <img> 😀',revision:2},after:{name:'Después Ω',revision:3}}});
const reply=(value,etag='"7"')=>new Response(JSON.stringify(value),{headers:{'Content-Type':'application/json',ETag:etag}});
function api(fetcher){const a=new RackClickApi(fetcher);a.actorId=actor;return a}
const from=(value,etag)=>api(async()=>reply(value,etag));
test('detalle GET exacto, sin caché/CSRF/mutación; nombre del actor actual separado del histórico',async()=>{
 const value=data(),a=api(async(path,init)=>{assert.equal(path,'/api/v1/admin/audit/'+id);assert.equal(init.cache,'no-store');assert.equal(init.credentials,'same-origin');assert.equal(init.method,undefined);assert.equal(init.body,undefined);assert.equal(init.headers,undefined);return reply(value)});
 assert.deepEqual(await readAuditDetail(a,event()),value);
});
test('alta y Systemhaus conservan ámbito y revisión histórica, no ETag actual',async()=>{
 const create=data();create.event.action='customer.create';create.detail.before=null;create.detail.after.revision=1;
 assert.deepEqual(await readAuditDetail(from(create),create.event),create);
 const house=data();house.event.action='systemhaus.rename';house.detail.revisionScope='systemhaus';house.detail.customerId=null;
 assert.deepEqual(await readAuditDetail(from(house),house.event),house);
 const same=data();same.detail.after.name=same.detail.before.name;
 assert.deepEqual(await readAuditDetail(from(same),event()),same);
});
test('unavailable conserva metadata para acciones no soportadas sin inventar campos',async()=>{
 const value=data();value.event.action='inventory.device.update';value.detail={status:'unavailable',revisionScope:null,customerId:null,before:null,after:null};
 assert.deepEqual(await readAuditDetail(from(value),value.event),value);
});
test('100 runas y Unicode descompuesto literales, IDs case-insensitive y precisión UTC equivalente',async()=>{
 const value=data();value.detail.after.name='😀'.repeat(100);value.detail.customerId=resource.toUpperCase();value.event.id=id.toUpperCase();value.event.occurredAt='2026-10-16T12:34:56.1234560Z';
 assert.deepEqual(await readAuditDetail(from(value),event()),value);
});
test('BOM U+FEFF se conserva como .NET; no se usa trim de JavaScript',async()=>{
 const value=data();value.detail.after.name='﻿Histórico';value.event.actor.userName='﻿';
 assert.deepEqual(await readAuditDetail(from(value),event()),value);
 const page={revision:7,events:[value.event],nextBeforeId:null};assert.deepEqual(await readAuditPage(from(page)),page);
});
const invalid={
 'top extra':v=>v.password='synthetic','etag revision unsafe':v=>v.revision=Number.MAX_SAFE_INTEGER+1,
 'event extra':v=>v.event.after_json={},'event zero':v=>v.event.id=zero,'other event':v=>v.event.id=other,
 'other resource':v=>v.event.resourceId=other,'other request':v=>v.event.requestId=other,'other actor':v=>v.event.actor.id=other,
 'actor secret':v=>v.event.actor.token='synthetic','actor empty':v=>v.event.actor.userName=' ',
 'other action':v=>v.event.action='customer.create','other UTC precision':v=>v.event.occurredAt='2026-10-16T12:34:56.1234561Z',
 'bad UTC date':v=>v.event.occurredAt='2026-02-30T12:34:56Z','detail extra':v=>v.detail.raw_json={},
 'unknown status':v=>v.detail.status='committed','wrong scope':v=>v.detail.revisionScope='systemhaus',
 'wrong customer':v=>v.detail.customerId=other,'zero customer':v=>v.detail.customerId=zero,'missing customer':v=>v.detail.customerId=null,
 'no before rename':v=>v.detail.before=null,'no after':v=>v.detail.after=null,'state extra':v=>v.detail.after.token='synthetic',
 'empty name':v=>v.detail.after.name='','trimmed name':v=>v.detail.after.name=' Name ',
 'control name':v=>v.detail.after.name='Name\nline','malformed UTF16':v=>v.detail.after.name='Name\ud800',
 'over name limit':v=>v.detail.after.name='😀'.repeat(101),'string revision':v=>v.detail.after.revision='3',
 'zero revision':v=>v.detail.before.revision=0,'gap revision':v=>v.detail.after.revision=4,
 'unsafe historical revision':v=>{v.detail.before.revision=Number.MAX_SAFE_INTEGER;v.detail.after.revision=Number.MAX_SAFE_INTEGER+1},
 'partial unavailable':v=>v.detail.status='unavailable'
};
for(const [label,mutate] of Object.entries(invalid))test('detalle rechaza '+label,async()=>{const value=data();mutate(value);await assert.rejects(readAuditDetail(from(value),event()),e=>e.code==='response_invalid')});
test('combinaciones inconsistentes alta/Systemhaus/acción desconocida son rechazadas',async()=>{
 for(const kind of ['createBefore','createRevision','houseCustomer','unknownAvailable']){
  const value=data(),input=event();
  if(kind.startsWith('create')){value.event.action=input.action='customer.create';value.detail.after.revision=1;if(kind==='createRevision'){value.detail.before=null;value.detail.after.revision=2}}
  if(kind==='houseCustomer'){value.event.action=input.action='systemhaus.rename';value.detail.revisionScope='systemhaus'}
  if(kind==='unknownAvailable')value.event.action=input.action='inventory.device.update';
  await assert.rejects(readAuditDetail(from(value),input),e=>e.code==='response_invalid');
 }
});
test('captura identidad antes de await; mutar evento seleccionado no cambia validación ni URL',async()=>{
 const selected=event(),value=data();let release;const pending=new Promise(resolve=>release=resolve);
 const a=api(async path=>{assert.equal(path,'/api/v1/admin/audit/'+id);await pending;return reply(value)});
 const result=readAuditDetail(a,selected);selected.id=other;selected.actor.id=other;selected.resourceId=other;selected.action='unknown';release();assert.deepEqual(await result,value);
});
test('identidad de sesión se comprueba antes/después; entrada inválida no envía HTTP',async()=>{
 let sent=0;const a=api(async()=>{sent++;a.actorId=other;return reply(data())});
 for(const value of [{...event(),id:zero},{...event(),after_json:{}},{...event(),occurredAt:'bad'}])await assert.rejects(readAuditDetail(a,value),e=>e.code==='request_invalid');
 await assert.rejects(readAuditDetail(a,event(),other),e=>e.code==='actor_changed');assert.equal(sent,0);
 await assert.rejects(readAuditDetail(a,event()),e=>e.code==='actor_changed');assert.equal(sent,1);
});
for(const etag of ['', '7', 'W/"7"', '"2"'])test('detalle rechaza ETag '+etag,async()=>assert.rejects(readAuditDetail(from(data(),etag),event()),e=>e.code==='response_invalid'));
test('errores HTTP/red se propagan sin datos ni éxito',async()=>{
 for(const status of [401,403,404,503])await assert.rejects(readAuditDetail(api(async()=>new Response('{"error":"synthetic"}',{status})),event()),e=>e.status===status);
 await assert.rejects(readAuditDetail(api(async()=>{throw Error('offline')}),event()),e=>e.status===0&&!e.uncertain);
});
