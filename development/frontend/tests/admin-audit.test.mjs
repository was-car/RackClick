import test from 'node:test';
import assert from 'node:assert/strict';
import {RackClickApi} from '../src/api.ts';
import {readAuditPage,validateAuditFilters} from '../src/admin-audit.ts';
const actor='12345678-1234-1234-1234-123456789abc',other='22345678-1234-1234-1234-123456789abc',zero='00000000-0000-0000-0000-000000000000';
const event=i=>({id:'00000000-0000-4000-8000-'+String(100-i).padStart(12,'0'),occurredAt:'2026-10-16T12:34:56.123456Z',actor:{id:actor,userName:'Name <img> Ä 😀'},requestId:actor,action:'legacy.literal',resourceId:other});
const page=()=>({revision:3,events:[event(0),event(1)],nextBeforeId:null});
const reply=(data,etag='"3"')=>new Response(JSON.stringify(data),{headers:{'Content-Type':'application/json',ETag:etag}});
function apiFor(fetcher){const api=new RackClickApi(fetcher);api.actorId=actor;return api}
const api=(data,etag)=>apiFor(async()=>reply(data,etag));
test('GET exacto sin caché, mutación ni storage; nombres/acciones literales',async()=>{const p=page(),a=apiFor(async(path,init)=>{assert.equal(path,'/api/v1/admin/audit?limit=50');assert.equal(init.cache,'no-store');assert.equal(init.credentials,'same-origin');assert.equal(init.method,undefined);assert.equal(init.body,undefined);assert.equal(init.headers,undefined);return reply(p)});assert.deepEqual(await readAuditPage(a),p)});
const invalid={
 'extra top':p=>p.after_json={},'revision zero':p=>p.revision=0,'unsafe revision':p=>p.revision=Number.MAX_SAFE_INTEGER+1,
 'events not array':p=>p.events={},'over limit':p=>p.events=Array.from({length:51},(_,i)=>event(i)),
 'zero event':p=>p.events[0].id=zero,'extra event':p=>p.events[0].after_json={},'bad request':p=>p.events[0].requestId='bad',
 'zero resource':p=>p.events[0].resourceId=zero,'extra actor':p=>p.events[0].actor.password='synthetic',
 'zero actor':p=>p.events[0].actor.id=zero,'blank name':p=>p.events[0].actor.userName=' ',
 'blank action':p=>p.events[0].action='','invalid calendar':p=>p.events[0].occurredAt='2026-02-30T12:34:56Z',
 'hour24':p=>p.events[0].occurredAt='2026-10-16T24:00:00Z','offset timestamp':p=>p.events[0].occurredAt='2026-10-16T12:34:56+00:00',
 'year zero':p=>p.events[0].occurredAt='0000-10-16T12:34:56Z','duplicate UUID casefold':p=>p.events[1].id=p.events[0].id.toUpperCase(),
 'reversed UUID tie':p=>p.events.reverse(),'reversed microseconds':p=>{p.events[0].occurredAt='2026-10-16T12:34:56.000001Z';p.events[1].occurredAt='2026-10-16T12:34:56.000002Z'},
 'cursor short page':p=>p.nextBeforeId=p.events.at(-1).id,'cursor empty page':p=>{p.events=[];p.nextBeforeId=actor}
};
for(const [label,mutate] of Object.entries(invalid))test('DTO rechaza '+label,async()=>{const p=page();mutate(p);await assert.rejects(readAuditPage(api(p)),e=>e.code==='response_invalid')});
for(const etag of ['', '3', 'W/"3"','"4"'])test('ETag inválido '+etag,async()=>assert.rejects(readAuditPage(api(page(),etag)),e=>e.code==='response_invalid'));
test('página50 exige cursor último y lo envía exclusivamente por ID',async()=>{const p={revision:3,events:Array.from({length:50},(_,i)=>event(i)),nextBeforeId:event(49).id};assert.deepEqual(await readAuditPage(api(p)),p);p.nextBeforeId=actor;await assert.rejects(readAuditPage(api(p)),e=>e.code==='response_invalid');const before={id:event(1).id,occurredAt:event(1).occurredAt},next={revision:9,events:[event(2)],nextBeforeId:null};const a=apiFor(async path=>{assert.equal(path,'/api/v1/admin/audit?limit=50&beforeId='+before.id);return reply(next,'"9"')});assert.deepEqual(await readAuditPage(a,before),next)});
test('cursor exclusivo rechaza repetición/retroceso y acepta fin vacío',async()=>{const before={id:event(1).id,occurredAt:event(1).occurredAt};await assert.rejects(readAuditPage(api(page()),before),e=>e.code==='response_invalid');assert.deepEqual(await readAuditPage(api({revision:3,events:[],nextBeforeId:null}),before),{revision:3,events:[],nextBeforeId:null})});
test('precisión submilisegundo y distintas longitudes fraccionarias',async()=>{const p=page();p.events[0].occurredAt='2026-10-16T12:34:56.000002Z';p.events[1].occurredAt='2026-10-16T12:34:56.0000019Z';assert.deepEqual(await readAuditPage(api(p)),p);p.events[0].occurredAt='2026-10-16T12:34:56.1Z';p.events[1].occurredAt='2026-10-16T12:34:56.100000Z';assert.deepEqual(await readAuditPage(api(p)),p)});
test('cursor inválido no envía y actor se comprueba antes/después de await',async()=>{let sent=0;const a=apiFor(async()=>{sent++;a.actorId=other;return reply(page())});for(const bad of [{id:zero,occurredAt:event(0).occurredAt},{id:actor,occurredAt:'bad'},{...event(0)}])await assert.rejects(readAuditPage(a,bad),e=>e.code==='request_invalid');await assert.rejects(readAuditPage(a,null,other),e=>e.code==='actor_changed');assert.equal(sent,0);await assert.rejects(readAuditPage(a),e=>e.code==='actor_changed');assert.equal(sent,1)});
test('errores de servidor/red se propagan sin fingir éxito',async()=>{for(const status of [401,403,404,503])await assert.rejects(readAuditPage(apiFor(async()=>new Response('{"error":"synthetic"}',{status}))),e=>e.status===status);await assert.rejects(readAuditPage(apiFor(async()=>{throw Error('offline')})),e=>e.status===0&&!e.uncertain)});

for(const [label,filters,query] of [
 ['actor',{actorId:actor.toUpperCase(),resourceId:''},'&actorId='+actor],
 ['resource',{actorId:'',resourceId:other.toUpperCase()},'&resourceId='+other],
 ['both',{actorId:actor,resourceId:other},'&actorId='+actor+'&resourceId='+other]
])test('filtros '+label+' por ID exacto y respuesta coincidente',async()=>{const a=apiFor(async(path,init)=>{assert.equal(path,'/api/v1/admin/audit?limit=50'+query);assert.equal(init.cache,'no-store');assert.equal(init.body,undefined);return reply(page())});assert.deepEqual(await readAuditPage(a,null,actor,filters),page())});
test('filtros inválidos no envían solicitudes y nunca se recortan silenciosamente',async()=>{let sent=0;const a=apiFor(async()=>{sent++;return reply(page())});const bad=[null,{}, {actorId:'',resourceId:'',extra:true},...['bad',zero,' '+actor,actor+' ',actor.replaceAll('-',''),'{'+actor+'}',null,7].map(id=>({actorId:id,resourceId:''})),{actorId:'',resourceId:zero}];for(const value of bad){assert.throws(()=>validateAuditFilters(value),e=>e.code==='audit_filter_invalid');await assert.rejects(readAuditPage(a,null,actor,value),e=>e.code==='audit_filter_invalid')}assert.equal(sent,0)});
for(const filters of [{actorId:other,resourceId:''},{actorId:'',resourceId:actor},{actorId:actor,resourceId:actor}])test('servidor devuelve otra selección: rechaza página',async()=>assert.rejects(readAuditPage(api(page()),null,actor,filters),e=>e.code==='response_invalid'));
test('cursor conserva ambos filtros; fin vacío filtrado es válido',async()=>{const before={id:event(1).id,occurredAt:event(1).occurredAt},p={revision:3,events:[],nextBeforeId:null};const a=apiFor(async path=>{assert.equal(path,'/api/v1/admin/audit?limit=50&beforeId='+before.id+'&actorId='+actor+'&resourceId='+other);return reply(p)});assert.deepEqual(await readAuditPage(a,before,actor,{actorId:actor,resourceId:other}),p)});
test('los filtros se capturan antes de await; un cambio externo no altera la selección en vuelo',async()=>{let release;const filters={actorId:actor,resourceId:other},a=apiFor(()=>new Promise(resolve=>{release=resolve}));const pending=readAuditPage(a,null,actor,filters);filters.actorId=other;filters.resourceId=actor;release(reply(page()));assert.deepEqual(await pending,page())});
test('todos los eventos deben coincidir con el filtro, no sólo el primero',async()=>{const p=page();p.events[1].actor.id=other;await assert.rejects(readAuditPage(api(p),null,actor,{actorId:actor,resourceId:''}),e=>e.code==='response_invalid')});
