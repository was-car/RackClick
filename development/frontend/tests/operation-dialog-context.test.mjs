import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {prepareCommand} from '../src/inventory-api.ts';
import {mutationRemainsUnconfirmed} from '../src/api.ts';
import {pendingRecord} from '../src/pending-journal.ts';
import {inventoryWords} from '../src/inventory-words.ts';
import {operationStatusWords} from '../src/inventory-operation-status-words.ts';

const id=n=>'34000000-0000-4000-8000-'+String(n).padStart(12,'0');
const pause=()=>{let resolve,entered;const wait=new Promise(r=>{resolve=r}),started=new Promise(r=>{entered=r});return{started,release:resolve,async block(){entered();await wait}}};
async function harness(options={}){
 const source=await readFile(process.env.RACKCLICK_DIALOG_SOURCE||new URL('../src/OperationDialog.jsx',import.meta.url),'utf8');
 const start=source.indexOf('export function OperationDialog('),end=source.indexOf('\n const locked =',start);assert.ok(start>=0&&end>start);
 const body=source.slice(start,end).replace('export function','function')+'\nreturn {submit,cancelPending,queryPending,refreshRevision,operation,preview,error,unconfirmed};}\nreturn OperationDialog;';
 const slots=[],effects=[],events=[],records=new Map();let cursor=0;
 const api={actorId:id(1),csrf:'synthetic',async request(){await options.preview?.();return{data:{customerId:customer,revision:4,confirmationToken:'synthetic',impact:{}}}}},customer=id(2),session={user:{id:id(1),userName:'synthetic-user'}};
 const operation=prepareCommand(api,customer,'operations.compensate',{operationId:id(3)},4);
 if(options.recovery!==false)records.set(operation.requestId,pendingRecord(operation,'undoGroups','synthetic'));
 let props={api,session,project:{customerId:customer,revision:4},lang:'es',recovery:options.recovery===false?null:records.get(operation.requestId),draft:{label:'undoGroups',initial:{},destructive:!!options.destructive,build:()=>({type:'operations.compensate',payload:{operationId:id(3)}})},onClose(){events.push('close')},async onCommit(){events.push('commit');await options.commit?.()},async onRefresh(){events.push('refresh');await options.refresh?.();return props.project},async onPendingChange(){events.push('pending');await options.pending?.()}};
 const useState=initial=>{const index=cursor++;if(!(index in slots))slots[index]=typeof initial==='function'?initial():initial;return[slots[index],value=>{slots[index]=typeof value==='function'?value(slots[index]):value}]};
 const useRef=initial=>{const index=cursor++;return slots[index]??={current:index===0&&initial===null?{showModal(){}}:initial}};
 const useEffect=(callback,deps)=>{const index=cursor++,previous=slots[index];if(!previous||deps.some((d,i)=>d!==previous.deps[i]))effects.push(()=>{previous?.cleanup?.();slots[index]={deps,cleanup:callback()}})};
 const result={customerId:customer,revision:5,requestId:operation.requestId,operationId:id(4),result:{resourceId:id(5)}};
 const env={useState,useRef,useEffect,inventoryWords,operationStatusWords,mutationRemainsUnconfirmed,pendingRecord,prepareCommand,
  window:{confirm:()=>true,addEventListener(){},removeEventListener(){}},
  pendingJournal:{async put(record){records.set(record.requestId,structuredClone(record));await options.put?.()},async remove(key,actor){events.push('remove:'+actor);await options.remove?.();records.delete(key)}},
  async executeCommand(_api,op){events.push('send');await options.send?.();return {...result,requestId:op.requestId}},
  async cancelPendingCommand(_api,op){events.push('cancel');await options.cancel?.();return {state:options.cancelState||'committed',operation:{...result,requestId:op.requestId}}},
  async readPendingCommand(){await options.query?.();return {state:options.queryState||'committed',operation:result}}
 };
 const component=new Function('env','const {'+Object.keys(env).join(',')+'}=env;\n'+body)(env);
 let current;
 function render(patch={}){props={...props,...patch};cursor=0;current=component(props);while(effects.length)effects.shift()();return current}
 function change(kind){if(kind==='actor'){api.actorId=id(99);render({session:{user:{id:id(99),userName:'other'}}})}else if(kind==='customer')render({project:{customerId:id(99),revision:4}});else if(kind==='api')render({api:{actorId:id(1),csrf:'other'}});else if(kind==='unmount'){for(const slot of slots)slot?.cleanup?.()}else throw Error(kind)}
 render();return{api,events,records,operation,props:()=>props,render,change,submit:()=>current.submit({preventDefault(){}}),cancel:()=>current.cancelPending(),query:()=>current.queryPending(),get current(){return current}};
}
const callbacks=events=>events.filter(e=>['commit','refresh','close'].includes(e));

test('a pending local put must not dispatch after actor/customer change or unmount',async()=>{
 for(const kind of ['actor','customer','unmount']){const gate=pause(),h=await harness({recovery:false,put:()=>gate.block()});const work=h.submit();await gate.started;h.change(kind);gate.release();await work;assert.equal(h.events.includes('send'),false,kind);assert.equal(h.records.size,1,kind);assert.deepEqual(callbacks(h.events),[],kind)}
});
test('a late mutation response must not apply to another actor/customer/API',async()=>{
 for(const kind of ['actor','customer','api']){const gate=pause(),h=await harness({send:()=>gate.block()});const work=h.submit();await gate.started;h.change(kind);gate.release();await work;assert.deepEqual(callbacks(h.events),[],kind);assert.equal(h.records.size,1,kind)}
});
test('a confirmed submit journal cleanup cannot apply callbacks to a new context',async()=>{
 const gate=pause(),h=await harness({remove:()=>gate.block()});const work=h.submit();await gate.started;h.change('actor');gate.release();await work;assert.deepEqual(callbacks(h.events),[]);assert.equal(h.records.size,0,'known terminal record may be cleared for its original actor');
});
test('cancel response after context change retains the unconfirmed original and applies no callbacks',async()=>{
 for(const kind of ['actor','customer','unmount']){const gate=pause(),h=await harness({cancel:()=>gate.block()});const original=structuredClone([...h.records.values()]);const work=h.cancel();await gate.started;h.change(kind);gate.release();await work;assert.deepEqual(callbacks(h.events),[],kind);assert.deepEqual([...h.records.values()],original,kind)}
});
test('cancel cleanup and pending callback boundaries do not refresh/close another context',async()=>{
 for(const boundary of ['remove','pending']){const gate=pause(),h=await harness({[boundary]:()=>gate.block(),cancelState:'cancelled'});const work=h.cancel();await gate.started;h.change('customer');gate.release();await work;assert.deepEqual(callbacks(h.events),[],boundary)}
});
test('returning A to B to A does not reactivate the same old draft',async()=>{
 const h=await harness({recovery:false}),original=h.props();h.change('customer');h.render({project:original.project});await h.submit();assert.equal(h.events.includes('send'),false);assert.equal(h.records.size,0);
});
test('a draft cannot silently adopt the next user as its original actor',async()=>{
 const h=await harness({recovery:false});h.change('actor');await h.submit();assert.equal(h.events.includes('send'),false);assert.equal(h.records.size,0);
});
test('failed cancellation keeps the exact pending intent including a definitive 403',async()=>{
 const h=await harness({cancel:async()=>{throw {status:403,uncertain:false}}}),original=structuredClone([...h.records.values()]);await h.cancel();assert.deepEqual([...h.records.values()],original);assert.deepEqual(callbacks(h.events),[]);
});
test('normal submit and recovery preserve one original request and terminal cleanup',async()=>{
 for(const recovery of [false,true]){const h=await harness({recovery});await h.submit();assert.equal(h.events.filter(e=>e==='send').length,1);assert.equal(h.records.size,0);assert.deepEqual(callbacks(h.events),['commit','close'])}
});
test('normal cancellation distinguishes already committed from cancelled without an inverse write',async()=>{
 for(const state of ['committed','cancelled']){const h=await harness({cancelState:state});await h.cancel();assert.deepEqual(callbacks(h.events),[state==='committed'?'commit':'refresh','close']);assert.equal(h.records.size,0);assert.equal(h.events.includes('send'),false)}
});
test('query regression retains notRecorded and recovers a terminal receipt in the original context',async()=>{
 for(const state of ['committed','cancelled','notRecorded']){const h=await harness({queryState:state});await h.query();assert.equal(h.events.includes('send')||h.events.includes('cancel'),false);assert.equal(h.records.size,state==='notRecorded'?1:0);assert.deepEqual(callbacks(h.events),state==='committed'?['commit','close']:state==='cancelled'?['refresh']:[])}
});

test('a known later revision prevents creating a new intent without replacing the loaded snapshot',async()=>{
 for(const patch of [{knownRevision:6},{project:{customerId:id(2),revision:6}}]){const h=await harness({recovery:false});h.render(patch);await h.submit();assert.equal(h.records.size,0);assert.equal(h.events.includes('send'),false);assert.equal(h.render().error.status,412)}
});
test('observed write or read authority loss prevents a new intent',async()=>{
 for(const patch of [{writeAllowed:false},{authorityLost:true}]){const h=await harness({recovery:false});h.render(patch);await h.submit();assert.equal(h.records.size,0);assert.equal(h.events.includes('send'),false);assert.equal(h.render().error.status,403)}
});
test('a late preview cannot become eligible after a newer revision is observed',async()=>{
 const gate=pause(),h=await harness({recovery:false,destructive:true,preview:()=>gate.block()});const work=h.submit();await gate.started;h.render({knownRevision:5});gate.release();await work;assert.equal(h.render().preview,null);assert.equal(h.records.size,0);assert.equal(h.events.includes('send'),false);
});
test('eligibility loss during journal or pending-list wait prevents first dispatch and retains exact intent',async()=>{
 for(const boundary of ['put','pending'])for(const patch of [{knownRevision:5},{writeAllowed:false},{authorityLost:true}]){const gate=pause(),h=await harness({recovery:false,[boundary]:()=>gate.block()});const work=h.submit();await gate.started;const original=structuredClone([...h.records.values()]);h.render(patch);gate.release();await work;assert.equal(h.events.includes('send'),false);assert.deepEqual([...h.records.values()],original);const state=h.render();assert.equal(state.operation.requestId,original[0].requestId);assert.equal(state.unconfirmed,true)}
});
test('a later revision never rewrites a recovered request and does not block lookup or cancellation',async()=>{
 for(const action of ['query','cancel','submit']){const h=await harness();h.render({knownRevision:9,project:{customerId:id(2),revision:9}});const original=structuredClone(h.operation);await h[action]();assert.deepEqual(h.operation,original);assert.equal(h.records.size,0);assert.equal(h.events.filter(e=>e==='send').length,action==='submit'?1:0)}
});
test('write authority loss blocks retry but leaves original lookup and cancellation available',async()=>{
 const h=await harness(),original=structuredClone([...h.records.values()]);h.render({writeAllowed:false});await h.submit();assert.equal(h.events.includes('send'),false);assert.deepEqual([...h.records.values()],original);await h.query();assert.equal(h.records.size,0);
 const c=await harness();c.render({writeAllowed:false});await c.cancel();assert.equal(c.events.includes('cancel'),true);assert.equal(c.records.size,0);
});
