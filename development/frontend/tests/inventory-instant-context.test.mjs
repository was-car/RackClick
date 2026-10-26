import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {prepareCommand} from '../src/inventory-api.ts';
import {pendingRecord} from '../src/pending-journal.ts';
import {RevisionGate} from '../src/revision-gate.ts';
const id=n=>'56000000-0000-4000-8000-'+String(n).padStart(12,'0');
const pause=()=>{let release,enter;const ready=new Promise(r=>enter=r),wait=new Promise(r=>release=r);return{ready,release,async block(){enter();await wait}}};
async function harness(options={}){
 const source=await readFile(process.env.RACKCLICK_PANEL_SOURCE||new URL('../src/InventoryPanel.jsx',import.meta.url),'utf8');
 const part=(from,to)=>{const a=source.indexOf(from),b=source.indexOf(to,a);assert.ok(a>=0&&b>a,from);return source.slice(a,b)};
 const assignment=source.split('\n').find(l=>l.trimStart().startsWith('panelContext.current='))||'';
 const guards=source.includes('function panelInContext(')?part('function panelInContext(','const refreshPending ='):'';
 const body=guards+part('const refreshPending =','const refreshSharedPending=')+part('async function refresh(','useEffect(() => { mounted.current')+part('async function committed(','function open(');
 const records=new Map(),events=[],mounted={current:true},api={actorId:id(1)},session={user:{id:id(1)}},customer={id:id(2),revision:4},initial={customerId:id(2),revision:4,racks:[],devices:[],ports:[],portGroups:[],connections:[]};
 const env={api,session,customer,snapshot:initial,canEdit:true,blocked:false,readAuthorityLost:false,observedRevision:4,
  mounted,pendingEpoch:{current:0},reads:{current:new RevisionGate()},useCallback:f=>f,pendingRecord,
  prepareCommand(...args){if(options.prepareError)throw options.prepareError;return prepareCommand(...args)},
  pendingJournal:{async put(row){records.set(row.requestId,structuredClone(row));events.push('put');await options.put?.()},async remove(key,actor){await options.remove?.();if(records.get(key)?.actorId===actor)records.delete(key);events.push('remove')},async list(actor){events.push('list');await options.list?.();return [...records.values()].filter(r=>r.actorId===actor)}},
  async executeCommand(_api,operation){events.push('send');await options.send?.();if(options.failure)throw options.failure;return{customerId:operation.customerId,revision:5,requestId:operation.requestId,operationId:id(8),result:{resourceId:id(9)}}},
  async loadProject(){events.push('read');await options.read?.();return {...initial,revision:5}},
  compensationCandidate(){events.push('candidate');return{revision:5}},candidateMatches:()=>true,rememberCompensation(){events.push('remember')},draft:null,recovery:null,
  ...Object.fromEntries(['setBusy','setError','setUndoCandidate','setUndoStale','setSnapshot','setActiveRackId','setLoading','setStatus','setSelection','setReconnect','setSelectedDevices','setPending','setJournalReady','onRevision'].map(name=>[name,value=>events.push(name+':'+(typeof value==='object'?JSON.stringify(value):String(value)))]))
 };
 const create=new Function('env',`let {api,session,customer,snapshot,canEdit,blocked,readAuthorityLost,observedRevision}=env;const {${Object.keys(env).filter(k=>!['api','session','customer','snapshot','canEdit','blocked','readAuthorityLost','observedRevision'].includes(k)).join(',')}}=env;
 const panelOrigin={current:{api,actorId:session.user.id,customerId:customer.id}},panelContext={current:null},instantInFlight={current:false},instantIntent={current:null};
 function sync(){${assignment}} sync();
 ${body}
 return {instant,refreshPending,refresh,committed,patch(value){if(value.api)api=value.api;if(value.session)session=value.session;if(value.customer)customer=value.customer;if(value.snapshot)snapshot=value.snapshot;if('canEdit'in value)canEdit=value.canEdit;if('blocked'in value)blocked=value.blocked;if('readAuthorityLost'in value)readAuthorityLost=value.readAuthorityLost;if('observedRevision'in value)observedRevision=value.observedRevision;sync()}};`);
 const methods=create(env),switchContext=kind=>{if(kind==='actor'){api.actorId=id(99);methods.patch({session:{user:{id:id(99)}}})}else if(kind==='customer')methods.patch({customer:{id:id(99),revision:4}});else if(kind==='api')methods.patch({api:{actorId:id(1)}});else if(kind==='unmount')mounted.current=false;else throw Error(kind)};
 return{...methods,events,records,api,switchContext,call:()=>methods.instant('rack.update',{id:id(3),name:'synthetic'},'edit')};
}
const late=events=>events.filter(e=>e==='send'||e==='read'||e==='candidate'||e==='remember'||e==='list'||e.startsWith('set')||e.startsWith('onRevision'));
test('instant cannot dispatch after identity change or unmount during journal put',async()=>{
 for(const kind of ['actor','customer','api','unmount']){const gate=pause(),h=await harness({put:()=>gate.block()}),work=h.call();await gate.ready;const original=structuredClone([...h.records.values()]);h.switchContext(kind);const count=h.events.length;gate.release();assert.equal(await work,false,kind);assert.deepEqual(late(h.events.slice(count)),[],kind);assert.deepEqual([...h.records.values()],original,kind)}
});
test('instant retains uncertainty and avoids callbacks after a late server response in another context',async()=>{
 for(const kind of ['actor','customer','api','unmount']){const gate=pause(),h=await harness({send:()=>gate.block()}),work=h.call();await gate.ready;const original=structuredClone([...h.records.values()]);h.switchContext(kind);const count=h.events.length;gate.release();assert.equal(await work,false,kind);assert.deepEqual(late(h.events.slice(count)),[],kind);assert.deepEqual([...h.records.values()],original,kind)}
});
test('terminal journal cleanup cannot confirm the next view',async()=>{
 const gate=pause(),h=await harness({remove:()=>gate.block()}),work=h.call();await gate.ready;h.switchContext('customer');const count=h.events.length;gate.release();assert.equal(await work,false);assert.deepEqual(late(h.events.slice(count)),[]);assert.equal(h.records.size,0);
});
test('refresh completing after unmount cannot publish revision, candidate or pending callbacks',async()=>{
 const gate=pause(),h=await harness({read:()=>gate.block()}),work=h.call();await gate.ready;h.switchContext('unmount');const count=h.events.length;gate.release();assert.equal(await work,false);assert.deepEqual(late(h.events.slice(count)),[]);assert.equal(h.records.size,0);
});
test('eligibility lost during pending-list wait stops first dispatch without rewriting intent',async()=>{
 for(const patch of [{observedRevision:6},{canEdit:false},{readAuthorityLost:true}]){const gate=pause(),h=await harness({list:()=>gate.block()}),work=h.call();await gate.ready;const original=structuredClone([...h.records.values()]);h.patch(patch);gate.release();assert.equal(await work,false);assert.equal(h.events.includes('send'),false);assert.deepEqual([...h.records.values()],original)}
});
test('two immediate actions create only one operation before a render',async()=>{
 const gate=pause(),h=await harness({put:()=>gate.block()}),one=h.call(),two=h.call();await gate.ready;gate.release();assert.deepEqual(await Promise.all([one,two]),[true,false]);assert.equal(h.events.filter(e=>e==='send').length,1);
});
test('preparation errors are contained and release busy state',async()=>{
 const h=await harness({prepareError:{status:422,code:'synthetic_invalid'}});assert.equal(await h.call(),false);assert.equal(h.records.size,0);assert.ok(h.events.includes('setBusy:false'));
});
test('normal commit, known error and uncertain response preserve their distinct journal outcomes',async()=>{
 for(const failure of [null,{status:422,uncertain:false},{status:0,uncertain:true}]){const h=await harness({failure});assert.equal(await h.call(),!failure);assert.equal(h.records.size,failure?.uncertain?1:0);assert.equal(h.events.includes('remember'),!failure)}
});
test('an obsolete pending-list rejection cannot replace a newer successful read',async()=>{
 const gate=pause();let n=0;const h=await harness({list:async()=>{if(++n===1){await gate.block();throw {code:'old_storage_failure'}}}}),first=h.refreshPending();await gate.ready;await h.refreshPending();const count=h.events.length;gate.release();await first;assert.deepEqual(h.events.slice(count),[]);
});
test('an uncertain result blocks another instant action before the pending state can render',async()=>{
 const h=await harness({failure:{status:0,uncertain:true}});assert.equal(await h.call(),false);const original=structuredClone([...h.records.values()]);assert.equal(await h.call(),false);assert.equal(h.events.filter(e=>e==='send').length,1);assert.deepEqual([...h.records.values()],original);
 const known=await harness({failure:{status:422,uncertain:false}});await known.call();await known.call();assert.equal(known.events.filter(e=>e==='send').length,2);assert.equal(known.records.size,0);
});
