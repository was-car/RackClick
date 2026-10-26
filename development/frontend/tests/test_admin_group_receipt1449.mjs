import test from 'node:test';
import assert from 'node:assert/strict';
import { RackClickApi } from '../src/api.ts';
import { createGroup, groupStatus, cancelGroup } from '../src/admin-groups.ts';
import { groupCreationReceipt, completeGroupCreation, groupReceiptBlock } from '../src/admin-group-receipt.ts';

const actor='12345678-1234-1234-1234-123456789abc',id='22345678-1234-1234-1234-123456789abc',other='42345678-1234-1234-1234-123456789abc';
const draft={actorId:actor,requestId:'32345678-1234-1234-1234-123456789abc',kind:'userGroup',name:'\u0085  <b>Ä e\u0301 名</b>  \u0085',revision:7};
const saved={requestId:draft.requestId,systemhausRevision:8,resource:{id,kind:draft.kind,name:'<b>Ä e\u0301 名</b>'}};
const cancelled={requestId:draft.requestId,state:'cancelled',operation:null};
const receipt=()=>groupCreationReceipt(saved,draft,actor);
const response=data=>new Response(JSON.stringify(data),{headers:{'Content-Type':'application/json'}});
const apiFor=handler=>{const api=new RackClickApi(handler);api.actorId=actor;api.csrf='synthetic';return api;};
const allowed=(patch={})=>({receipt:receipt(),actor,apiActor:actor,snapshot:{revision:8,userGroups:[{id}],customerGroups:[{id:other}]},ready:true,busy:false,pending:false,current:true,...patch});

test('receipt projects the exact committed UUID/type/literal Unicode name without arbitrary fields',()=>{
 const value=groupCreationReceipt({...saved,password:'excluded',resource:{...saved.resource,token:'excluded'}},draft,actor);
 assert.deepEqual(value,{actorId:actor,requestId:draft.requestId,groupId:id,name:saved.resource.name,kind:'userGroup',revision:8});
 assert.equal(Object.isFrozen(value),true);assert.equal(JSON.stringify(value).includes('excluded'),false);
 assert.notEqual(value.name,draft.name);
});

test('notRecorded, malformed or wrong-actor results cannot establish a commit; real cancellation has no receipt',()=>{
 for(const value of [null,{state:'notRecorded'},{...saved,state:'notRecorded'},{...saved,state:'pending'},{...saved,requestId:other},{...saved,systemhausRevision:9},{...saved,resource:{...saved.resource,id:'not-an-id'}},{...saved,resource:{...saved.resource,kind:'customerGroup'}},{...saved,resource:{...saved.resource,name:'same-looking replacement'}}])
  assert.throws(()=>groupCreationReceipt(value,draft,actor),error=>error.code==='response_invalid');
 assert.throws(()=>groupCreationReceipt(saved,draft,other),error=>error.code==='actor_changed');
 assert.equal(groupCreationReceipt(cancelled,draft,actor),null);
 assert.throws(()=>groupCreationReceipt({...cancelled,requestId:other},draft,actor),error=>error.code==='response_invalid');
});

test('actual POST/status/cancel-committed adapters recover exactly the same original group',async()=>{
 const calls=[],api=apiFor(async(url,init)=>{calls.push({url,init});return response(init?.method==='POST'&&!url.endsWith('/cancel')?saved:{requestId:draft.requestId,state:'committed',operation:saved});});
 for(const value of [await createGroup(api,draft),await groupStatus(api,draft),await cancelGroup(api,draft)])assert.deepEqual(groupCreationReceipt(value,draft,actor),receipt());
 assert.equal(calls[0].url,'/api/v1/admin/user-groups');assert.equal(calls[1].url,calls[0].url+'/operations/'+draft.requestId);assert.equal(calls[2].url,calls[1].url+'/cancel');
 assert.deepEqual(JSON.parse(calls[0].init.body),{name:draft.name});assert.deepEqual(JSON.parse(calls[2].init.body),{name:draft.name});
});

test('actual customer-group adapters preserve type; notRecorded and cancellation never become receipts',async()=>{
 const customer={...draft,kind:'customerGroup'},stored={...saved,resource:{...saved.resource,kind:'customerGroup'}},paths=[];
 const result=await createGroup(apiFor(async url=>{paths.push(url);return response(stored);}),customer);
 assert.equal(groupCreationReceipt(result,customer,actor).kind,'customerGroup');assert.deepEqual(paths,['/api/v1/admin/customer-groups']);
 assert.equal(await groupStatus(apiFor(async()=>response({requestId:draft.requestId,state:'notRecorded',operation:null})),draft),null);
 assert.equal(groupCreationReceipt(await cancelGroup(apiFor(async()=>response(cancelled)),draft),draft,actor),null);
 await assert.rejects(()=>createGroup(apiFor(async()=>new Response('{"error":"forbidden"}',{status:403})),draft),error=>error.status===403);
 await assert.rejects(()=>createGroup(apiFor(async()=>{throw Error('lost reply');}),draft),error=>error.uncertain);
});

test('remember precedes journal failure and preserves the pending original, with continuation blocked',async()=>{
 const state={receipt:null,pending:true},events=[];
 await assert.rejects(()=>completeGroupCreation(saved,draft,actor,{
  current:()=>true,remember:value=>{state.receipt=value;events.push('remember')},removeJournal:async()=>{events.push('remove');throw Error('local cleanup failed')},clearPending:()=>{state.pending=false},reload:()=>assert.fail('must not reload after failed cleanup')
 }),/local cleanup failed/);
 assert.deepEqual(events,['remember','remove']);assert.deepEqual(state.receipt,receipt());assert.equal(state.pending,true);
 assert.equal(groupReceiptBlock(allowed({...state})),'pending');
});

test('failed refresh retains committed receipt, while a successful retry recovers the same UUID without create',async()=>{
 const state={receipt:null,pending:true,snapshot:null},events=[];
 await assert.rejects(()=>completeGroupCreation(saved,draft,actor,{
  current:()=>true,remember:value=>{state.receipt=value;events.push('remember')},removeJournal:async()=>events.push('remove'),clearPending:()=>{state.pending=false;events.push('clear')},reload:async()=>{events.push('reload');throw Error('read failed')}
 }),/read failed/);
 assert.deepEqual(events,['remember','remove','clear','reload']);assert.deepEqual(state.receipt,receipt());assert.equal(state.pending,false);
 assert.equal(groupReceiptBlock(allowed({...state})),'refresh');
 const recovered=await groupStatus(apiFor(async()=>response({requestId:draft.requestId,state:'committed',operation:saved})),draft);
 assert.deepEqual(groupCreationReceipt(recovered,draft,actor),state.receipt);
});

test('commit then cleanup failure then notRecorded preserves evidence until same-UUID committed recovery',async()=>{
 const state={receipt:null,pending:true},events=[];let cleanupFails=true;
 const steps={current:()=>true,remember:value=>{state.receipt=value;events.push('remember')},removeJournal:async()=>{events.push('remove');if(cleanupFails)throw Error('cleanup failed')},clearPending:()=>{state.pending=false;events.push('clear')},reload:()=>events.push('reload')};
 await assert.rejects(()=>completeGroupCreation(saved,draft,actor,steps),/cleanup failed/);
 const first=state.receipt;assert.equal(state.pending,true);assert.equal(first.groupId,id);
 const unknown=await groupStatus(apiFor(async()=>response({requestId:draft.requestId,state:'notRecorded',operation:null})),draft);
 await completeGroupCreation(unknown,draft,actor,steps);
 assert.equal(state.receipt,first);assert.equal(state.pending,true);assert.deepEqual(events,['remember','remove']);
 cleanupFails=false;const recovered=await groupStatus(apiFor(async()=>response({requestId:draft.requestId,state:'committed',operation:saved})),draft);
 await completeGroupCreation(recovered,draft,actor,steps);
 assert.deepEqual(state.receipt,first);assert.equal(state.pending,false);assert.deepEqual(events,['remember','remove','remember','remove','clear','reload']);
});

test('generation invalidation before remember or during cleanup cannot affect the new actor state',async()=>{
 let active=false;const events=[];
 const steps={current:()=>active,remember:()=>events.push('remember'),removeJournal:async()=>{events.push('remove');active=false},clearPending:()=>events.push('clear'),reload:()=>events.push('reload')};
 await completeGroupCreation(saved,draft,actor,steps);assert.deepEqual(events,[]);
 active=true;await completeGroupCreation(saved,draft,actor,steps);assert.deepEqual(events,['remember','remove']);
 const api=apiFor(async()=>{api.actorId=other;return response(saved)});
 await assert.rejects(()=>createGroup(api,draft),error=>error.code==='actor_changed');
});

test('continuation requires current actor, no pending work, fresh revision and exact UUID in the correct type',()=>{
 assert.equal(groupReceiptBlock(allowed()),null);
 for(const patch of [{receipt:null},{actor:other},{apiActor:other},{current:false},{snapshot:null},{snapshot:{revision:7,userGroups:[{id}],customerGroups:[]}}])assert.equal(groupReceiptBlock(allowed(patch)),'refresh');
 assert.equal(groupReceiptBlock(allowed({ready:false})),'loading');assert.equal(groupReceiptBlock(allowed({busy:true})),'loading');assert.equal(groupReceiptBlock(allowed({pending:true,busy:true})),'pending');
 assert.equal(groupReceiptBlock(allowed({snapshot:{revision:9,userGroups:[{id:other,name:saved.resource.name}],customerGroups:[{id,name:saved.resource.name}]}})),'missing');
 const customerReceipt={...receipt(),kind:'customerGroup'};
 assert.equal(groupReceiptBlock(allowed({receipt:customerReceipt})),'missing');
 assert.equal(groupReceiptBlock(allowed({receipt:customerReceipt,snapshot:{revision:9,userGroups:[{id:other}],customerGroups:[{id}]}})),null);
});
