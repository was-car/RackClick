import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {ApiError,RackClickApi} from '../src/api.ts';
import {categoryNames,categoryPairs,categoryPair,categorySwatches,validCategoryColors,sameCategoryColors,validUserCategoryColors,validCategoryColorsDraft,prepareCategoryColors,confirmedCategoryColors,categoryColorsOutcome,readUserCategoryColors,mutateCategoryColors,categoryColorsStatus,cancelCategoryColors} from '../src/user-category-colors.ts';
import {categoryColorsJournal} from '../src/user-category-colors-journal.ts';
import {userCategoryColorsWords} from '../src/user-category-colors-words.ts';
const id=n=>'00000000-0000-4000-8000-'+String(n).padStart(12,'0'),actor=id(1),other=id(2);
const snapshot=(revision=0,colors={},ownerId=actor)=>({kind:'userCategoryColors',ownerId,revision,colors});
const api=fetcher=>Object.assign(new RackClickApi(fetcher),{actorId:actor,csrf:'synthetic'});
const response=(data,n=data.revision)=>new Response(JSON.stringify(data),{headers:{ETag:'"category-colors-'+n+'"','Content-Type':'application/json'}});
const draft=(colors={'Other↔Other':'#3b82f6'},rev=0)=>prepareCategoryColors(actor,snapshot(rev),colors);
const receipt=(d,changed=true)=>({kind:'userCategoryColors',ownerId:d.actorId,revision:d.revision+(changed?1:0),requestId:d.requestId,operationId:id(3),result:{colors:{...d.colors},changed}});
const outcome=(d,state='committed',revision=9)=>({state,ownerId:d.actorId,revision,requestId:d.requestId,operation:state==='committed'?receipt(d):null});
test('RC9 exact categories, ordinal symmetric/self pairs and ten closed swatches',()=>{
 assert.deepEqual(categoryNames,['Patch Panel','Switch','Router','Firewall','Server','NAS/SAN','Other']);assert.equal(categoryPairs.length,28);assert.equal(new Set(categoryPairs.map(p=>p.key)).size,28);
 assert.deepEqual(categorySwatches,['#ffffff','#d1d5db','#fbbf24','#3b82f6','#10b981','#ef4444','#a855f7','#f97316','#06b6d4','#000000']);
 for(const {a,b,key} of categoryPairs){assert.equal(categoryPair(b,a),key);assert.ok(validCategoryColors({[key]:'#3b82f6'}))}
 assert.ok(validCategoryColors(Object.fromEntries(categoryPairs.map(p=>[p.key,'#10b981']))));
 for(const v of [null,[],{'Switch↔Patch Panel':'#3b82f6'},{'Other ↔ Other':'#3b82f6'},{'Other↔Other':'#aabbcc'},{'Other↔Other':'#FFFFFF'},{'Other↔Other':null},JSON.parse('{"__proto__":"#3b82f6"}')])assert.equal(validCategoryColors(v),false);
 assert.ok(sameCategoryColors({'Other↔Other':'#3b82f6','Router↔Switch':'#10b981'},{'Router↔Switch':'#10b981','Other↔Other':'#3b82f6'}));assert.equal(sameCategoryColors({},{'Other↔Other':'#3b82f6'}),false);
});
test('snapshot requires exact owner/family/fields, safe revisions and empty absence at zero',()=>{
 assert.ok(validUserCategoryColors(snapshot(),actor));assert.ok(validUserCategoryColors(snapshot(1,{'Other↔Other':'#3b82f6'}),actor));
 for(const mutate of [x=>x.ownerId=other,x=>x.customerId=other,x=>x.kind='userPreferences',x=>x.revision=2**53,x=>x.revision=-1,x=>x.colors={'Other↔Other':'#3b82f6'},x=>delete x.colors]){const x=snapshot();mutate(x);assert.equal(validUserCategoryColors(x,actor),false)}
});
test('GET is actor scoped without customer parameters and verifies ETag and late authority',async()=>{
 let call;const a=api(async(path,init)=>{call={path,init};return response(snapshot())});assert.deepEqual(await readUserCategoryColors(a),snapshot());assert.equal(call.path,'/api/v1/me/category-colors');assert.equal(call.init.body,undefined);
 await assert.rejects(readUserCategoryColors(api(async()=>response(snapshot(),1))),e=>e.code==='response_invalid');
 const b=api(async()=>{b.actorId=other;return response(snapshot())});await assert.rejects(readUserCategoryColors(b,actor),e=>e.code==='actor_changed');
});
test('prepared replacement is immutable, cloned, and contains only original public actor/revision/request/map',()=>{
 const colors={'Other↔Other':'#3b82f6'},d=draft(colors);colors['Other↔Other']='#ef4444';assert.equal(d.colors['Other↔Other'],'#3b82f6');assert.ok(Object.isFrozen(d)&&Object.isFrozen(d.colors));assert.deepEqual(Object.keys(d).sort(),['actorId','colors','requestId','revision']);assert.ok(validCategoryColorsDraft(d));
 assert.equal(validCategoryColorsDraft({...d,customerId:other}),false);assert.equal(validCategoryColorsDraft({...d,colors:{gn:'#3b82f6'}}),false);assert.throws(()=>prepareCategoryColors(other,snapshot(),{}));assert.throws(()=>prepareCategoryColors(actor,snapshot(),{'Other↔Other':'#ABCDEF'}));
});
test('POST retry and cancel preserve exact body, CSRF, actor, revision and idempotency after loss',async()=>{
 const d=draft(),calls=[],a=api(async(path,init)=>{calls.push({path,body:init.body,headers:init.headers});if(calls.length===1)throw Error('lost');return response(path.endsWith('/cancel')?outcome(d):receipt(d))});
 await assert.rejects(mutateCategoryColors(a,d),e=>e.uncertain);await mutateCategoryColors(a,d);assert.deepEqual(calls[0],calls[1]);await cancelCategoryColors(a,d);assert.deepEqual(calls[2].headers,calls[0].headers);assert.equal(calls[2].body,calls[0].body);assert.equal(calls[0].headers['If-Match'],'"category-colors-0"');assert.equal(calls[0].headers['X-RackClick-Actor'],actor);assert.deepEqual(JSON.parse(calls[0].body),{colors:{'Other↔Other':'#3b82f6'}});
});
test('reset all at revision zero is a valid recorded no-op, as is a safe-limit no-op',()=>{
 const d=draft({});assert.equal(confirmedCategoryColors(receipt(d,false),d).revision,0);const last=draft({},Number.MAX_SAFE_INTEGER);assert.equal(confirmedCategoryColors(receipt(last,false),last).revision,Number.MAX_SAFE_INTEGER);assert.throws(()=>confirmedCategoryColors(receipt(last,true),last));
});
test('receipts fail closed on forged colors, actors, requests, extras or false revision arithmetic',()=>{
 const d=draft();assert.equal(confirmedCategoryColors(receipt(d),d).revision,1);
 for(const mutate of [x=>x.ownerId=other,x=>x.kind='preferences',x=>x.requestId=id(9),x=>x.result.colors={'Router↔Switch':'#3b82f6'},x=>x.result.colors={'Other↔Other':'#3b82f6','Router↔Switch':'#3b82f6'},x=>x.result.changed=false,x=>x.result.extra=true,x=>x.revision=2**53,x=>x.extra=true,x=>x.operationId='00000000-0000-0000-0000-000000000000']){const x=receipt(d);mutate(x);assert.throws(()=>confirmedCategoryColors(x,d),e=>e.uncertain)}
});
test('historical receipt and status revision differ; notRecorded never confirms/cancels; etags bind every response',async()=>{
 const d=draft(),o=outcome(d);assert.equal(categoryColorsOutcome(o,d).operation.revision,1);assert.equal((await categoryColorsStatus(api(async()=>response(o)),d)).revision,9);assert.equal(categoryColorsOutcome(outcome(d,'notRecorded'),d).operation,null);await assert.rejects(cancelCategoryColors(api(async()=>response(outcome(d,'notRecorded'))),d),e=>e.uncertain);
 for(const mutate of [x=>x.revision=0,x=>x.operation.ownerId=other,x=>x.state='saved',x=>x.customerId=other]){const x=outcome(d);mutate(x);assert.throws(()=>categoryColorsOutcome(x,d))}
 for(const fn of [mutateCategoryColors,categoryColorsStatus,cancelCategoryColors])await assert.rejects(fn(api(async()=>response(fn===mutateCategoryColors?receipt(d):o,99)),d),e=>e.code==='response_invalid'&&e.uncertain);
});
test('all transport functions reject a foreign actor before send and check again after await',async()=>{
 const d=draft(),a=api(()=>{throw Error('must not send')});a.actorId=other;for(const fn of [mutateCategoryColors,categoryColorsStatus,cancelCategoryColors])await assert.rejects(fn(a,d),e=>e.code==='actor_changed');
 for(const fn of [mutateCategoryColors,categoryColorsStatus,cancelCategoryColors]){const b=api(async()=>{b.actorId=other;return response(fn===mutateCategoryColors?receipt(d):outcome(d))});await assert.rejects(fn(b,d),e=>e.code==='actor_changed')}
});
test('IndexedDB palette family isolates actors and refuses replacement/deletion of another original',async()=>{
 const records=new Map();let created=false;globalThis.indexedDB={open(name){assert.equal(name,'RackClick.UserCategoryColors.v1');const r={};queueMicrotask(()=>{r.result={createObjectStore(){created=true},close(){},transaction(){const tx={aborted:false,abort(){this.aborted=true;queueMicrotask(()=>this.onabort?.())},objectStore(){return{get(key){const read={};queueMicrotask(()=>{read.result=records.get(key);read.onsuccess?.();queueMicrotask(()=>{if(!tx.aborted)tx.oncomplete?.()})});return read},put(d){records.set(d.actorId,structuredClone(d))},delete(key){records.delete(key)}}}};return tx}};if(!created)r.onupgradeneeded?.();r.onsuccess?.()});return r}};
 try{const d=draft();await categoryColorsJournal('write',actor,d);assert.deepEqual(await categoryColorsJournal('read',actor),d);assert.equal(await categoryColorsJournal('read',other),null);await assert.rejects(categoryColorsJournal('write',actor,{...d,requestId:id(9)}));await assert.rejects(categoryColorsJournal('remove',actor,{...d,colors:{}}));await assert.rejects(categoryColorsJournal('write',actor,{...d,csrf:'secret'}));await categoryColorsJournal('remove',actor,d);assert.equal(await categoryColorsJournal('read',actor),null);records.set(actor,{...d,ownerId:actor});await assert.rejects(categoryColorsJournal('read',actor))}finally{delete globalThis.indexedDB}
});
test('EN/DE/ES recovery and palette controls have matching complete word sets',()=>{for(const lang of ['de','es'])assert.deepEqual(Object.keys(userCategoryColorsWords[lang]).sort(),Object.keys(userCategoryColorsWords.en).sort())});

const flush=async()=>{for(let i=0;i<20;i++)await Promise.resolve()};
async function harness(overrides={}){
 const source=await readFile(new URL('../src/UserCategoryColors.jsx',import.meta.url),'utf8'),body=source.slice(source.indexOf('export function useUserCategoryColors('),source.indexOf('\nexport function PersonalPalette(')).replace('export function','function');
 const slots=[],effects=[],reads=[],records=new Map(),mutations=[];let cursor=0;
 const useState=initial=>{const i=cursor++;if(!(i in slots))slots[i]=typeof initial==='function'?initial():initial;return[slots[i],v=>{slots[i]=typeof v==='function'?v(slots[i]):v}]},useRef=initial=>{const i=cursor++;return slots[i]??={current:initial}},useEffect=(callback,deps)=>{const i=cursor++,old=slots[i];if(!old||deps.some((v,j)=>v!==old.deps[j]))effects.push(()=>{old?.cleanup?.();slots[i]={deps,cleanup:callback()}})};
 const journal=overrides.journal||(async(action,owner,d)=>{if(action==='read')return records.get(owner)||null;if(action==='write'){records.set(owner,d);return d}records.delete(owner);return null});
 const read=overrides.read||((_api,owner)=>new Promise(resolve=>reads.push({owner,resolve})));
 const mutate=overrides.mutate||(async(_api,d)=>{mutations.push(d);return receipt(d)});
 const hook=new Function('useState','useEffect','useRef','categoryColorsJournal','readUserCategoryColors','prepareCategoryColors','mutateCategoryColors','categoryColorsStatus','cancelCategoryColors','validCategoryColors','ApiError',body+';return useUserCategoryColors')(useState,useEffect,useRef,journal,read,prepareCategoryColors,mutate,overrides.status||(async(_a,d)=>outcome(d)),overrides.cancel||(async(_a,d)=>outcome(d,'cancelled')),validCategoryColors,ApiError);
 const a=api(()=>{}),props={api:a,actorId:actor,userName:'synthetic',generation:0};let currentProps=props;
 const render=(p=currentProps)=>{currentProps=p;cursor=0;const value=hook(p);while(effects.length)effects.shift()();return value};return{render,props,a,reads,records,mutations};
}
test('hook starts fail closed, reads only authenticated palette and never writes implicitly or anonymous storage',async()=>{
 const h=await harness();assert.equal(h.render().disabled,true);await flush();h.reads[0].resolve(snapshot());await flush();let s=h.render();assert.equal(s.ready,true);assert.deepEqual(s.colors,{});assert.equal(h.mutations.length,0);h.a.actorId='';s=h.render({...h.props,actorId:undefined});await s.save({'Other↔Other':'#ef4444'});await flush();assert.deepEqual(h.render().colors,{});assert.equal(h.mutations.length,0);
});
test('hook applies only current GET after validated POST, never draft or historical replay colors',async()=>{
 const h=await harness();h.render();await flush();h.reads[0].resolve(snapshot());await flush();const save=h.render().save({'Other↔Other':'#3b82f6'});await flush();let s=h.render();assert.deepEqual(s.colors,{});assert.equal(s.disabled,true);assert.equal(s.pending.colors['Other↔Other'],'#3b82f6');assert.equal(h.reads.length,2);h.reads[1].resolve(snapshot(9,{'Router↔Switch':'#ef4444'}));await save;await flush();s=h.render();assert.deepEqual(s.colors,{'Router↔Switch':'#ef4444'});assert.equal(s.notice,'saved');assert.equal(s.pending,null);
});
test('a rejected receipt preserves the old palette and original journal without an unearned GET/success',async()=>{
 const h=await harness({mutate:async(_a,d)=>confirmedCategoryColors({...receipt(d),result:{colors:{'Other↔Other':'#06b6d4'},changed:true}},d)});h.render();await flush();h.reads[0].resolve(snapshot());await flush();await h.render().save({'Other↔Other':'#3b82f6'});await flush();const s=h.render();assert.deepEqual(s.colors,{});assert.equal(s.error.code,'response_invalid');assert.equal(s.notice,'');assert.equal(s.pending.colors['Other↔Other'],'#3b82f6');assert.equal(h.reads.length,1);assert.equal(h.records.size,1);
});
test('A→B→A drops late read successes/errors/finalizers and exposes no former owner colors',async()=>{
 const h=await harness();h.render();await flush();h.reads[0].resolve(snapshot(1,{'Other↔Other':'#3b82f6'}));await flush();const late=h.render().reload();await flush();h.a.actorId=other;assert.deepEqual(h.render({...h.props,actorId:other}).colors,{});await flush();h.reads[2].resolve(snapshot(2,{'Router↔Switch':'#a855f7'},other));await flush();assert.deepEqual(h.render().colors,{'Router↔Switch':'#a855f7'});h.a.actorId=actor;h.render(h.props);await flush();h.reads[3].resolve(snapshot(5,{'Server↔Switch':'#06b6d4'}));await flush();h.reads[1].resolve(snapshot(99,{'Other↔Other':'#ffffff'}));await late;await flush();const s=h.render();assert.equal(s.data.revision,5);assert.deepEqual(s.colors,{'Server↔Switch':'#06b6d4'});assert.equal(s.error,null);assert.equal(s.busy,false);
});
test('lost response keeps exact original; notRecorded never frees it or permits replacing the map',async()=>{
 const calls=[],h=await harness({mutate:async(_a,d)=>{calls.push(d);throw new ApiError(0,'network_unconfirmed',true)},status:async(_a,d)=>outcome(d,'notRecorded')});h.render();await flush();h.reads[0].resolve(snapshot());await flush();await h.render().save({'Other↔Other':'#3b82f6'});await flush();const original=h.render().pending;await h.render().save({'Router↔Switch':'#ef4444'});assert.equal(calls.length,1);await h.render().recover('query');await flush();assert.equal(h.render().notice,'notRecorded');assert.equal(h.render().pending.requestId,original.requestId);await h.render().recover('retry');await flush();assert.deepEqual(calls,[original,original]);assert.deepEqual(h.render().colors,{});
});
test('generation/suspension changes while durable write awaits prevent stale sends and hide palette immediately',async()=>{
 for(const suspended of [false,true]){let release;const h=await harness({journal:async(action)=>{if(action==='read')return null;if(action==='write')await new Promise(resolve=>release=resolve);return null}});h.render();await flush();h.reads[0].resolve(snapshot(1,{'Other↔Other':'#3b82f6'}));await flush();const old=h.render().save({'Other↔Other':'#ef4444'});await flush();if(!suspended)h.a.actorId=other;assert.deepEqual(h.render({...h.props,actorId:suspended?actor:other,suspended,generation:1}).colors,{});await flush();release();await old;await flush();assert.equal(h.mutations.length,0);assert.equal(h.render().error,null)}
});
test('cancelled original waits for current GET before reporting cancellation or releasing its journal',async()=>{
 const h=await harness({mutate:async()=>{throw new ApiError(0,'network_unconfirmed',true)}});h.render();await flush();h.reads[0].resolve(snapshot(3,{'Other↔Other':'#3b82f6'}));await flush();await h.render().save({});await flush();const cancel=h.render().recover('cancel');await flush();assert.equal(h.render().pending.colors['Other↔Other'],undefined);assert.equal(h.render().notice,'');assert.equal(h.records.size,1);h.reads[1].resolve(snapshot(7,{'NAS/SAN↔Switch':'#fbbf24'}));await cancel;await flush();assert.equal(h.render().notice,'cancelled');assert.equal(h.records.size,0);assert.deepEqual(h.render().colors,{'NAS/SAN↔Switch':'#fbbf24'});
});
test('late same-user reauthentication invalidates shared API/session on A→B and A→logout→A',async()=>{
 for(const nextActor of [other,actor]){const h=await harness();let release,invalidated=0;const props={...h.props,onAuthenticationInvalidated:()=>{invalidated++;h.a.actorId='';h.a.csrf=''}};h.a.login=async()=>{await new Promise(resolve=>release=resolve);h.a.actorId=actor;h.a.csrf='late-A';return{user:{id:actor}}};h.render(props);await flush();h.reads[0].resolve(snapshot(1,{'Server↔Switch':'#3b82f6'}));await flush();const old=h.render().authenticate('synthetic');await flush();h.a.actorId='';h.render({...props,actorId:undefined,generation:1});await flush();h.a.actorId=nextActor;h.a.csrf='new-session';h.render({...props,actorId:nextActor,generation:2});await flush();release();await old;await flush();assert.equal(invalidated,1);assert.equal(h.a.actorId,'');assert.equal(h.a.csrf,'');assert.equal(h.render().data,null);assert.equal(h.mutations.length,0)}
});

test('new palette transport never injects automatic preference into inventory creates or reconnect',async()=>{
 const source=await readFile(new URL('../src/InventoryPanel.jsx',import.meta.url),'utf8');
 assert.ok(source.includes("'connections.create', { fromPortId: selection.pid, toPortId: portId, color: nextColor"));assert.ok(source.includes('prepareConnectionBatch(current,form.pairs,form.confirmReserved,nextColor)'));assert.ok(!source.includes('categoryColors'));
});
test('port969 controller remains byte exact and only navigation/active dialog extension is added',async()=>{
 const {createHash}=await import('node:crypto');const reference=await readFile(new URL('../../../reference/historical/UserPortColors-port969.jsx',import.meta.url));assert.equal(createHash('sha256').update(reference).digest('hex'),'cddc4ed099943c0b5cfa1e5c51481885e1eec7f32b375239a9a48ce50a70ca3e');const old=reference.toString('utf8').replaceAll('\r\n','\n');const current=(await readFile(new URL('../src/UserPortColors.jsx',import.meta.url),'utf8')).replaceAll('\r\n','\n');
 const expected=old.replace('export function UserPortColors({state,lang,onClose})','export function UserPortColors({state,lang,onClose,active=true,paletteNavigation})').replace('useEffect(()=>{dialog.current.showModal();return()=>dialog.current?.close()},[]);','useEffect(()=>{if(active)dialog.current.showModal();else dialog.current.close();return()=>dialog.current?.close()},[active]);').replace('</h2></div><p>{t.help}</p>','</h2></div>{paletteNavigation}<p>{t.help}</p>');assert.equal(current,expected);
});

test('failed reload keeps confirmed display but blocks editing until a new authenticated GET succeeds',async()=>{
 let failed=false;const h=await harness({read:async()=>{if(failed)throw new ApiError(503,'synthetic_unavailable');return snapshot(1,{'Other↔Other':'#3b82f6'})}});h.render();await flush();assert.equal(h.render().disabled,false);failed=true;await h.render().reload();await flush();let s=h.render();assert.equal(s.disabled,true);assert.equal(s.ready,false);assert.deepEqual(s.colors,{'Other↔Other':'#3b82f6'});assert.equal(s.error.status,503);failed=false;await s.reload();await flush();assert.equal(h.render().disabled,false);
});
