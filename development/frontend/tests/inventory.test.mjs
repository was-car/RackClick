import test from 'node:test';
import assert from 'node:assert/strict';
import { RackClickApi, mutationRemainsUnconfirmed } from '../src/api.ts';
import { validProject, projectToRc9, batchPortIds } from '../src/inventory-model.ts';
import { prepareCommand, executeCommand, loadProject, cancelPendingCommand } from '../src/inventory-api.ts';
import { pendingRecord, validPendingRecord } from '../src/pending-journal.ts';
import { RevisionGate } from '../src/revision-gate.ts';
import { inventoryWords } from '../src/inventory-words.ts';
const id = n => '00000000-0000-4000-8000-' + String(n).padStart(12,'0');
const customerId=id(1),actor=id(2);
const named=(n,name='Repeated')=>({id:id(n),name,properties:{}});
function fixture(){return {customerId,revision:3,sites:[named(3)],buildings:[{...named(4),siteId:id(3)}],rooms:[{...named(5),buildingId:id(4)}],racks:[{...named(6),roomId:id(5),sizeU:12,location:''}],devices:[{...named(7),kind:'rackEquipment',rackId:id(6),roomId:null,sizeU:1,sortOrder:0,poeBudget:null},{...named(8),kind:'dose',rackId:null,roomId:id(5),sizeU:null,sortOrder:0,poeBudget:null}],portGroups:[{id:id(9),deviceId:id(7),type:'rj45',name:'A',prefix:'A',sortOrder:0},{id:id(10),deviceId:id(7),type:'rj45',name:'B',prefix:'B',sortOrder:1},{id:id(11),deviceId:id(8),type:'rj45',name:'C',prefix:'C',sortOrder:0}],ports:[[12,7,9],[13,7,10],[14,8,11]].map(([n,d,g])=>({id:id(n),deviceId:id(d),groupId:id(g),type:'rj45',gn:1,sortOrder:0,label:'',status:'free',poe:false,watts:null,color:null,face:'auto',powerRole:'unspecified',properties:{}})),connections:[{id:id(15),fromPortId:id(12),toPortId:id(14),note:'Room cable',color:'#123456',patch:'tested',properties:{}}]};}
const response=(body,status=200,headers={})=>new Response(JSON.stringify(body),{status,headers:{'Content-Type':'application/json',...headers}});
function adapter(fetcher){const api=new RackClickApi(fetcher);api.actorId=actor;api.csrf='synthetic-token';return api;}
const committed=op=>({customerId,requestId:op.requestId,operationId:id(90),revision:4,result:{resourceId:id(91)}});
test('projection retains distinct UUIDs for duplicate names and gn; room objects consume no rack U',()=>{
 const snapshot=fixture(), before=JSON.stringify(snapshot); assert.equal(validProject(snapshot,customerId),true);
 const view=projectToRc9(snapshot,'Client'); assert.equal(view.racks[0].devs.length,1);assert.equal(view.devices.get(id(8)).u,null);assert.equal(view.devices.get(id(7)).ports.length,2);assert.notEqual(view.serverEndpoints[id(12)],view.serverEndpoints[id(13)]);assert.equal(view.crossConns[0].patchStatus,'tested');assert.equal(JSON.stringify(snapshot),before);
});
test('batch selection accepts IDs in exact device/group and rejects gn, foreign group or duplicate IDs',()=>{
 const p=fixture();assert.deepEqual(batchPortIds(p,id(7),id(9),[id(12)]).portIds,[id(12)]);
 for(const ids of [[1],[id(13)],[id(12),id(12)],[]])assert.throws(()=>batchPortIds(p,id(7),id(9),ids));
 assert.throws(()=>batchPortIds(p,id(8),id(9),[id(12)]));
});
test('snapshot rejects mismatched customer, dangling endpoints, fake room U and wrong group ownership',()=>{
 for(const mutate of [p=>p.customerId=id(99),p=>p.connections[0].toPortId=id(99),p=>p.devices[1].sizeU=1,p=>p.ports[0].groupId=id(11),p=>p.connections.push({...p.connections[0],id:id(16)})]){const p=fixture();mutate(p);assert.equal(validProject(p,customerId),false);}
});
test('snapshot ETag must match revision',async()=>{const api=adapter(async()=>response(fixture(),200,{ETag:'"2"'}));await assert.rejects(loadProject(api,customerId),e=>e.code==='response_invalid');});
test('command retry preserves exact UUID/body/actor/revision after lost response then 401/403/412',async()=>{
 let op;const calls=[];const api=adapter(async(url,init)=>{calls.push(init);if(calls.length===1)throw Error('lost');if(calls.length<5)return response({error:'denied'},[0,0,401,403,412][calls.length]);return response(committed(op));});
 op=prepareCommand(api,customerId,'site.create',{name:'One'},3);let pending=false;
 for(let i=0;i<4;i++){try{await executeCommand(api,op);assert.fail();}catch(e){pending=mutationRemainsUnconfirmed(pending,e);assert.equal(pending,true);}}
 assert.equal((await executeCommand(api,op)).revision,4);assert.equal(new Set(calls.map(c=>c.body)).size,1);assert.equal(new Set(calls.map(c=>c.headers['Idempotency-Key'])).size,1);assert.equal(calls[0].headers['X-RackClick-Actor'],actor);assert.equal(calls[0].headers['If-Match'],'"3"');
});
test('command rejects malformed successful response as uncertain',async()=>{const api=adapter(async()=>response({ok:true}));await assert.rejects(executeCommand(api,prepareCommand(api,customerId,'site.create',{name:'One'},3)),e=>e.uncertain);});
test('journal strips transport secrets and binds route/customer/request/actor immutably',()=>{
 const api=adapter(),op=prepareCommand(api,customerId,'site.create',{name:'One'},3),record=pendingRecord({...op,csrf:'SECRET',password:'SECRET'},'create','One');assert.equal(JSON.stringify(record).includes('SECRET'),false);assert.equal(validPendingRecord(record,actor),true);
 for(const mutate of [r=>r.actorId=id(99),r=>r.customerId=id(99),r=>r.operation.path='/customers/'+id(99)+'/commands',r=>r.operation.actorId=id(99),r=>r.operation.requestId=id(99),r=>r.operation.etag='*']){const changed=structuredClone(record);mutate(changed);assert.equal(validPendingRecord(changed,actor),false);}
});
test('foundation name operation is durable without storing user password/session',()=>{const api=adapter(),record=pendingRecord(api.prepare('create','Once',3),'create','Once');assert.equal(validPendingRecord(record,actor),true);assert.equal(record.customerId,undefined);});
test('cancellation binds original body/revision/actor and accepts only authoritative matched fence',async()=>{
 let op;const calls=[];const api=adapter(async(url,init)=>{calls.push({url,init});return response({state:'cancelled',customerId,requestId:op.requestId});});op=prepareCommand(api,customerId,'site.create',{name:'One'},3);assert.equal((await cancelPendingCommand(api,op)).state,'cancelled');assert.ok(calls[0].url.endsWith('/operations/'+op.requestId+'/cancel'));assert.equal(calls[0].init.body,op.body);assert.equal(calls[0].init.headers['If-Match'],op.etag);assert.equal(calls[0].init.headers['Idempotency-Key'],op.requestId);
 for(const state of ['notRecorded','unknown']){const other=adapter(async()=>response({state,customerId,requestId:op.requestId}));await assert.rejects(cancelPendingCommand(other,op),e=>e.uncertain);}
 const wrong=adapter(async()=>response({state:'cancelled',customerId:id(99),requestId:op.requestId}));await assert.rejects(cancelPendingCommand(wrong,op),e=>e.uncertain);
});
test('cancellation recovers original commit and different actor cannot submit fence',async()=>{let op;let sent=0;const api=adapter(async()=>{sent++;return response({state:'committed',customerId,requestId:op.requestId,operation:committed(op)});});op=prepareCommand(api,customerId,'site.create',{name:'One'},3);assert.equal((await cancelPendingCommand(api,op)).operation.revision,4);api.actorId=id(99);await assert.rejects(cancelPendingCommand(api,op),e=>e.code==='actor_changed');assert.equal(sent,1);});
test('late revision N cannot overwrite post-commit N+1, including racing refreshes',()=>{const gate=new RevisionGate(),old=gate.begin();gate.confirm(4);const fresh=gate.begin();assert.equal(gate.accept(fresh,4),true);assert.equal(gate.accept(old,3),false);const later=gate.begin();assert.equal(gate.accept(later,3),false);assert.equal(gate.revision,4);});
test('inventory EN/DE/ES translations have matching keys',()=>{for(const lang of ['de','es'])assert.deepEqual(Object.keys(inventoryWords[lang]).sort(),Object.keys(inventoryWords.en).sort());});
