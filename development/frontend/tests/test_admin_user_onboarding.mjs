import test from 'node:test';
import assert from 'node:assert/strict';
import { RackClickApi } from '../src/api.ts';
import { createUser, userStatus, cancelUser } from '../src/admin-users.ts';
import { userCreationReceipt, completeUserCreation, chooseAdminUser, userOnboardingBlock, visibleUserCreationReceipt } from '../src/admin-user-onboarding.ts';
import { onboardingWords } from '../src/admin-user-onboarding-words.ts';

const actor='12345678-1234-1234-1234-123456789abc',user='22345678-1234-1234-1234-123456789abc',other='42345678-1234-1234-1234-123456789abc';
const draft={actorId:actor,requestId:'32345678-1234-1234-1234-123456789abc',username:'  MiXeD Ä e\u0301 名  ',revision:7};
const saved={requestId:draft.requestId,systemhausRevision:8,resource:{id:user,userName:'mixed ä é 名',active:true}};
const cancelled={requestId:draft.requestId,state:'cancelled',operation:null};
const names=['state','password','sessions','effective','members'];
const guards=()=>Object.fromEntries(names.map(name=>[name,()=>false]));
const receipt=()=>userCreationReceipt(saved,draft,actor);
const continuation=(extra={})=>({receipt:receipt(),actor,apiActor:actor,snapshot:{revision:8,users:[{id:user},{id:other}]},listState:'current',ready:true,busy:false,pending:false,groupsMounted:true,selectedUserId:other,guardNames:names,guards:guards(),...extra});
const apiFor=handler=>{const api=new RackClickApi(handler);api.actorId=actor;api.csrf='fixture';return api;};
const response=data=>new Response(JSON.stringify(data),{headers:{'Content-Type':'application/json'}});

test('validated receipt uses saved Unicode name and UUID, projects no password or extra API fields',()=>{
 const actual=userCreationReceipt({...saved,password:'not part of receipt',resource:{...saved.resource,token:'excluded'}},draft,actor);
 assert.deepEqual(actual,{actorId:actor,requestId:draft.requestId,userId:user,userName:saved.resource.userName,revision:8});
 assert.equal(Object.isFrozen(actual),true);assert.notEqual(actual.userName,draft.username);
 assert.equal(JSON.stringify(actual).includes('excluded'),false);assert.equal(JSON.stringify(actual).includes('password'),false);
});

test('notRecorded, unknown, uncertain and malformed commits cannot become a receipt',()=>{
 for(const data of [null,{state:'notRecorded'},{...saved,state:'notRecorded'},{...saved,state:'unknown'}, {...saved,state:'pending'}, {...saved,requestId:other}, {...saved,systemhausRevision:9}, {...saved,resource:{...saved.resource,id:'not-an-id'}}])
  assert.throws(()=>userCreationReceipt(data,draft,actor),e=>e.code==='response_invalid');
 assert.throws(()=>userCreationReceipt(saved,draft,other),e=>e.code==='actor_changed');
 assert.equal(userCreationReceipt(cancelled,draft,actor),null);
 assert.throws(()=>userCreationReceipt({...cancelled,requestId:other},draft,actor),e=>e.code==='response_invalid');
});

test('actual create, status committed and cancel committed adapters all produce the same receipt',async()=>{
 const calls=[],api=apiFor(async(url,init)=>{calls.push({url,init});return response(init?.method==='POST'&&!url.endsWith('/cancel')?saved:{requestId:draft.requestId,state:'committed',operation:saved});});
 const results=[await createUser(api,draft,'Synthetic-password-1209'),await userStatus(api,draft),await cancelUser(api,draft)];
 for(const result of results)assert.deepEqual(userCreationReceipt(result,draft,actor),receipt());
 assert.equal(calls[0].url,'/api/v1/admin/users');assert.equal(calls[1].url,'/api/v1/admin/users/operations/'+draft.requestId);assert.equal(calls[2].url,calls[1].url+'/cancel');
 assert.deepEqual(JSON.parse(calls[2].init.body),{username:draft.username});
});

test('actual notRecorded and real cancellation do not offer a new account',async()=>{
 assert.equal(await userStatus(apiFor(async()=>response({requestId:draft.requestId,state:'notRecorded',operation:null})),draft),null);
 const outcome=await cancelUser(apiFor(async()=>response(cancelled)),draft);assert.equal(userCreationReceipt(outcome,draft,actor),null);
 await assert.rejects(()=>createUser(apiFor(async()=>new Response('{"error":"username_exists"}',{status:409})),draft,'Synthetic-password-1209'),e=>e.status===409);
 await assert.rejects(()=>createUser(apiFor(async()=>{throw Error('lost');}),draft,'Synthetic-password-1209'),e=>e.uncertain&&e.code==='network_unconfirmed');
});

test('commit receipt survives failed journal removal and retains the exact pending request',async()=>{
 const state={receipt:null,pending:draft,listState:'stale'},events=[];
 await assert.rejects(()=>completeUserCreation(saved,draft,actor,{
  current:()=>true,remember:value=>{state.receipt=value;events.push('receipt');},
  removeJournal:async()=>{events.push('remove');throw Error('journal unavailable');},
  clearPending:()=>{state.pending=null;events.push('clear');},reload:async()=>{state.listState='current';events.push('reload');}
 }),/journal unavailable/);
 assert.deepEqual(events,['receipt','remove']);assert.equal(state.pending,draft);assert.deepEqual(state.receipt,receipt());
 assert.equal(userOnboardingBlock(continuation({...state,pending:!!state.pending})),'pending');
});

test('commit receipt survives failed fresh read and continuation remains unavailable until refresh',async()=>{
 const state={receipt:null,pending:draft,listState:'stale'};
 await assert.rejects(()=>completeUserCreation(saved,draft,actor,{
  current:()=>true,remember:value=>{state.receipt=value;},removeJournal:async()=>{},clearPending:()=>{state.pending=null;},reload:async()=>{state.listState='unavailable';throw Error('read failed');}
 }),/read failed/);
 assert.equal(state.pending,null);assert.deepEqual(state.receipt,receipt());assert.equal(userOnboardingBlock(continuation({...state,pending:false})),'refresh');
 state.listState='current';assert.equal(userOnboardingBlock(continuation({...state,pending:false})),null);
});

test('committed recovery can clear a failed journal later; cancellation clears an old receipt',async()=>{
 const state={receipt:receipt(),pending:draft,listState:'stale'},steps={current:()=>true,remember:value=>{state.receipt=value;},removeJournal:async()=>{},clearPending:()=>{state.pending=null;},reload:async()=>{state.listState='current';}};
 await completeUserCreation(saved,draft,actor,steps);assert.equal(state.pending,null);assert.deepEqual(state.receipt,receipt());
 await completeUserCreation(cancelled,draft,actor,steps);assert.equal(state.receipt,null);
});

test('invalid result never clears the journal or refreshes a list',async()=>{
 let touched=false;await assert.rejects(()=>completeUserCreation({...saved,state:'notRecorded'},draft,actor,{current:()=>true,remember:()=>{touched=true;},removeJournal:async()=>{touched=true;},clearPending:()=>{touched=true;},reload:async()=>{touched=true;}}),e=>e.code==='response_invalid');assert.equal(touched,false);
});

test('old mount or actor generation cannot remember or clear results even after A→B→A',async()=>{
 const first={actor},second={actor:other},third={actor};let currentScope=first,release,remembered=0,cleared=0,reloaded=0;
 const steps={current:()=>currentScope===first,remember:()=>{remembered++;},removeJournal:()=>new Promise(resolve=>{release=resolve;}),clearPending:()=>{cleared++;},reload:async()=>{reloaded++;}};
 const pending=completeUserCreation(saved,draft,actor,steps);assert.equal(remembered,1);
 currentScope=second;currentScope=third;release();await pending;assert.equal(cleared,0);assert.equal(reloaded,0);
 await completeUserCreation(saved,draft,actor,steps);assert.equal(remembered,1);
});

test('continuation requires the current actor, list, recorded ID and completed recovery',()=>{
 assert.equal(userOnboardingBlock(continuation()),null);
 for(const extra of [{apiActor:other},{actor:other},{listState:'stale'},{listState:'unavailable'},{snapshot:null},{snapshot:{revision:7,users:[{id:user}]}}])assert.equal(userOnboardingBlock(continuation(extra)),'refresh');
 for(const extra of [{ready:false},{busy:true},{listState:'loading'},{groupsMounted:false}])assert.equal(userOnboardingBlock(continuation(extra)),'loading');
 assert.equal(userOnboardingBlock(continuation({pending:true})),'pending');
 assert.equal(userOnboardingBlock(continuation({snapshot:{revision:8,users:[{id:other}]}})),'missing');
});

test('every synchronized guard blocks both continuation destinations, also for the same UUID',()=>{
 for(const selectedUserId of [other,user])for(const name of names){
  const blocked=guards();blocked[name]=()=>true;assert.equal(userOnboardingBlock(continuation({selectedUserId,guards:blocked})),'locked');
  delete blocked[name];assert.equal(userOnboardingBlock(continuation({selectedUserId,guards:blocked})),'locked');
 }
 let active=false;const blocked=guards();blocked.password=()=>active;const input=continuation({guards:blocked});assert.equal(userOnboardingBlock(input),null);active=true;assert.equal(userOnboardingBlock(input),'locked');
});

test('selection returns true only for a recorded target, synchronized guards protect retargeting',()=>{
 const selections=[],input={id:user,selectedUserId:other,snapshot:{revision:8,users:[{id:user}]},current:true,guardNames:names,guards:guards(),onSelect:id=>selections.push(id)};
 assert.equal(chooseAdminUser(input),true);assert.deepEqual(selections,[user]);
 for(const extra of [{current:false},{snapshot:null},{id:other},{guards:{...guards(),sessions:()=>true}},{guards:{}}])assert.equal(chooseAdminUser({...input,...extra}),false);
 assert.deepEqual(selections,[user]);
});

test('same user navigation need not retarget or erase drafts but continuation still checks all guards',()=>{
 let changes=0;const input={id:user,selectedUserId:user,snapshot:{revision:8,users:[{id:user}]},current:true,guardNames:names,guards:{...guards(),password:()=>true},onSelect:()=>{changes++;}};
 assert.equal(chooseAdminUser(input),true);assert.equal(changes,0);
 assert.equal(userOnboardingBlock(continuation({selectedUserId:user,guards:input.guards})),'locked');
 input.guards.password=()=>false;assert.equal(userOnboardingBlock(continuation({selectedUserId:user,guards:input.guards})),null);assert.equal(chooseAdminUser(input),true);assert.equal(changes,0);
 assert.equal(chooseAdminUser({...input,current:false}),false);assert.equal(chooseAdminUser({...input,snapshot:{revision:8,users:[]}}),false);
});

test('three locales expose the same closed copy keys without translating saved names',()=>{
 const keys=Object.keys(onboardingWords.en).sort();for(const lang of ['en','de','es']){assert.deepEqual(Object.keys(onboardingWords[lang]).sort(),keys);for(const text of Object.values(onboardingWords[lang]))assert.ok(typeof text==='string'&&text.length>0);}
 assert.equal(receipt().userName,saved.resource.userName);
});

test('authorization withdrawal hides the saved name and UUID while a transient reload keeps evidence blocked',()=>{
 const savedReceipt=receipt(),scope={actor,apiActor:actor,current:true,authorized:true};
 assert.equal(visibleUserCreationReceipt(savedReceipt,scope),savedReceipt);
 for(const extra of [{authorized:false},{current:false},{apiActor:other},{actor:other}])assert.equal(visibleUserCreationReceipt(savedReceipt,{...scope,...extra}),null);
 assert.equal(visibleUserCreationReceipt(savedReceipt,{...scope,authorized:false}),null);
 assert.equal(userOnboardingBlock(continuation({receipt:savedReceipt,listState:'unavailable'})),'refresh');
 assert.equal(visibleUserCreationReceipt(savedReceipt,scope),savedReceipt);
 assert.equal(userOnboardingBlock(continuation({receipt:savedReceipt,listState:'current'})),null);
});
