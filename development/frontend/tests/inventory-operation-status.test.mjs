import test from 'node:test';
import assert from 'node:assert/strict';
import {RackClickApi} from '../src/api.ts';
import {prepareCommand,readPendingCommand,rememberCompensation} from '../src/inventory-api.ts';
const id=n=>'00000000-0000-4000-8000-'+String(n).padStart(12,'0');
function fixture(){
 const calls=[],api=new RackClickApi(async(url,init)=>{calls.push({url,init});return Response.json(reply)});
 api.actorId=id(1);api.csrf='synthetic-test';
 const operation=prepareCommand(api,id(2),'operations.compensate',{operationId:id(3)},5);
 const result={customerId:id(2),revision:6,requestId:operation.requestId,operationId:id(4),result:{resourceId:id(5),compensationKind:'groupGrowth',removedPortIds:[id(6)],removedGroupIds:[],compensatedOperationId:id(3)}};
 let reply={state:'committed',customerId:id(2),requestId:operation.requestId,revision:8,operation:result};
 return {api,operation,result,calls,get reply(){return reply},set reply(value){reply=value}};
}
test('GET recovers the original receipt despite a later outer revision; never resends the mutation',async()=>{
 const f=fixture(),original=JSON.stringify(f.operation);assert.deepEqual((await readPendingCommand(f.api,f.operation)).operation,f.result);
 assert.equal(f.calls.length,1);assert.equal(f.calls[0].url,'/api/v1/customers/'+id(2)+'/operations/'+f.operation.requestId);
 assert.equal(f.calls[0].init.method,'GET');assert.equal(f.calls[0].init.body,undefined);assert.equal(f.calls[0].init.headers,undefined);
 assert.equal(f.calls[0].init.credentials,'same-origin');assert.equal(f.calls[0].init.cache,'no-store');assert.equal(JSON.stringify(f.operation),original);
});
test('notRecorded is nonterminal and never confirms cancellation',async()=>{
 const f=fixture();f.reply={...f.reply,state:'notRecorded',operation:null};assert.equal((await readPendingCommand(f.api,f.operation)).state,'notRecorded');
});
test('cancelled accepts its own cancellation operationId and a historical revision',async()=>{
 const f=fixture();f.reply={...f.reply,state:'cancelled',operationId:id(7),revision:5,operation:null};assert.equal((await readPendingCommand(f.api,f.operation)).state,'cancelled');
});
test('malformed status and receipts preserve uncertainty',async()=>{
 for(const mutate of [r=>r.state='unknown',r=>r.customerId=id(9),r=>r.requestId=id(9),r=>r.revision=0,r=>r.revision=5,r=>r.operation.requestId=id(9),r=>r.operation.result.removedPortIds=[],r=>r.operation.result.compensatedOperationId=id(9),r=>r.operation=null,r=>r.extra='unexpected']){
  const f=fixture();mutate(f.reply);await assert.rejects(readPendingCommand(f.api,f.operation),e=>e.code==='response_invalid'&&e.uncertain);
 }
 for(const state of ['notRecorded','cancelled']){
  const f=fixture();f.reply={...f.reply,state};await assert.rejects(readPendingCommand(f.api,f.operation),e=>e.uncertain);
 }
});
test('query reuses structural scope validation, including restored variants',async()=>{
 const f=fixture();f.result.result={resourceId:id(5),compensationKind:'groupReduction',restoredPortIds:[id(6)],restoredGroupIds:[],restoredConnectionIds:[],compensatedOperationId:id(3)};
 rememberCompensation({actorId:id(1),customerId:id(2),operationId:id(3),revision:5,deviceId:id(5),compensationKind:'groupReduction',portIds:[id(6)],groupIds:[],connectionIds:[]});
 assert.equal((await readPendingCommand(f.api,f.operation)).operation.result.compensationKind,'groupReduction');
 f.result.result.restoredPortIds=[id(9)];await assert.rejects(readPendingCommand(f.api,f.operation),e=>e.uncertain);
});
test('wrong actor before lookup sends no request',async()=>{
 const f=fixture();f.api.actorId=id(9);await assert.rejects(readPendingCommand(f.api,f.operation),e=>e.code==='actor_changed');assert.equal(f.calls.length,0);
});
test('actor changed during lookup cannot accept the former receipt',async()=>{
 const f=fixture();f.api.fetcher=async()=>{f.api.actorId=id(9);return Response.json(f.reply)};
 await assert.rejects(readPendingCommand(f.api,f.operation),e=>e.code==='actor_changed'&&e.uncertain);
});
test('aborted lookup cannot accept a late valid response',async()=>{
 const f=fixture(),controller=new AbortController();f.api.fetcher=async()=>{controller.abort();return Response.json(f.reply)};
 await assert.rejects(readPendingCommand(f.api,f.operation,controller.signal),e=>e.uncertain);
});
test('authorization and network failures never turn into a confirmed result',async()=>{
 for(const status of [401,403,404,503]){const f=fixture();f.api.fetcher=async()=>Response.json({error:'synthetic_denied'},{status});await assert.rejects(readPendingCommand(f.api,f.operation),e=>e.status===status)}
 const f=fixture();f.api.fetcher=async()=>{throw Error('synthetic disconnected')};await assert.rejects(readPendingCommand(f.api,f.operation),e=>e.code==='network_unconfirmed');
});
