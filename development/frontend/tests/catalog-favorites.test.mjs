import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {RackClickApi} from '../src/api.ts';
import {rc9CatalogVersion as catalogVersion,rc9CatalogSha256 as catalogSha256} from '../src/inventory-catalog.ts';
import {validFavorites,validFavoriteDraft,readCatalogFavorites,prepareFavorite,confirmedFavorite,favoriteOutcome,setCatalogFavorite,catalogFavoriteStatus,cancelCatalogFavorite} from '../src/catalog-favorites.ts';
import {favoriteJournal} from '../src/catalog-favorites-journal.ts';
import {favoriteWords} from '../src/catalog-favorites-words.ts';
const id=n=>'00000000-0000-4000-8000-'+String(n).padStart(12,'0'),actor=id(1),customer=id(2),other=id(3);
const aggregate=(revision=0,presetKeys=[])=>({kind:'catalogFavorites',customerId:customer,ownerId:actor,revision,catalogVersion,catalogSha256,presetKeys});
const response=(data,revision=0)=>new Response(JSON.stringify(data),{headers:{'Content-Type':'application/json',ETag:'"favorites-'+revision+'"'}});
const api=fetcher=>Object.assign(new RackClickApi(fetcher),{actorId:actor,csrf:'synthetic'});
const receipt=(d,changed=true)=>({kind:'catalogFavorites',ownerId:actor,revision:d.revision+(changed?1:0),requestId:d.requestId,operationId:id(8),result:{presetKey:d.presetKey,favorite:d.favorite,changed,catalogVersion:d.catalogVersion,catalogSha256:d.catalogSha256}});
test('empty personal aggregate has revision zero; closed DTO requires actor/context/canonical pin and ordinal unique keys',()=>{
 assert.equal(validFavorites(aggregate(),customer,actor),true);
 assert.equal(validFavorites(aggregate(4,['pdu','pp24','ups']),customer,actor),true);
 for(const mutate of [a=>a.ownerId=other,a=>a.customerId=other,a=>a.revision=-1,a=>a.revision=2**53,a=>a.extra=true,a=>a.catalogSha256='0'.repeat(64),a=>a.presetKeys=['ups','pdu'],a=>a.presetKeys=['pdu','pdu'],a=>a.presetKeys=['ct_custom']]){const a=aggregate();mutate(a);assert.equal(validFavorites(a,customer,actor),false)}
});
test('GET has no inventory If-Match, validates personal ETag, and rejects changed actor after awaiting',async()=>{
 let call;const a=api(async(url,init)=>{call={url,init};return response(aggregate())});await readCatalogFavorites(a,customer);assert.equal(call.url,'/api/v1/customers/'+customer+'/catalog/favorites');assert.equal(call.init.headers,undefined);
 await assert.rejects(readCatalogFavorites(api(async()=>response(aggregate(),1)),customer),e=>e.code==='response_invalid');
 const changed=api(async()=>{changed.actorId=other;return response(aggregate())});await assert.rejects(readCatalogFavorites(changed,customer,actor),e=>e.code==='actor_changed');
});
test('explicit immutable boolean intention has no inventory/name/secret context; no-op and changed receipts use separate revision rules',()=>{
 const before=aggregate(),d=prepareFavorite(actor,before,'pdu',true);assert.equal(d.revision,0);assert.ok(Object.isFrozen(d));assert.equal(before.presetKeys.length,0);assert.deepEqual(Object.keys(d).sort(),['actorId','catalogSha256','catalogVersion','favorite','presetKey','requestId','revision']);
 assert.equal(confirmedFavorite(receipt(d),d).revision,1);assert.equal(confirmedFavorite(receipt(d,false),d).revision,0);
 for(const mutate of [r=>r.customerId=customer,r=>r.ownerId=other,r=>r.revision=4,r=>r.requestId=id(9),r=>r.result.favorite=false,r=>r.result.changed='true',r=>r.result.extra=true]){const r=receipt(d);mutate(r);assert.throws(()=>confirmedFavorite(r,d),e=>e.uncertain)}
 assert.throws(()=>prepareFavorite(actor,before,'ct_custom',true));
});
test('lost response retries identical key/body/personal revision from another authorised context, not toggle',async()=>{
 const d=prepareFavorite(actor,aggregate(),'pdu',true),calls=[];const a=api(async(url,init)=>{calls.push({url,headers:init.headers,body:init.body});if(calls.length===1)throw Error('response lost');return response(receipt(d),1)});
 await assert.rejects(setCatalogFavorite(a,customer,d),e=>e.uncertain);await setCatalogFavorite(a,other,d);assert.equal(calls[0].body,calls[1].body);assert.deepEqual(calls[0].headers,calls[1].headers);assert.notEqual(calls[0].url,calls[1].url);assert.equal(calls[0].headers['If-Match'],'"favorites-0"');assert.deepEqual(Object.keys(JSON.parse(calls[0].body)).sort(),['catalogSha256','catalogVersion','favorite','presetKey']);
});
test('status outer revision is current, committed operation remains historical; cancellation sends original intent and ETag',async()=>{
 const d=prepareFavorite(actor,aggregate(),'pdu',true),outcome={state:'committed',ownerId:actor,revision:7,requestId:d.requestId,operation:receipt(d)};assert.equal(favoriteOutcome(outcome,d).operation.revision,1);
 let call;const a=api(async(url,init)=>{call={url,init};return response(outcome,7)});await catalogFavoriteStatus(a,customer,d);await cancelCatalogFavorite(a,other,d);assert.equal(call.init.headers['If-Match'],'"favorites-0"');assert.equal(call.init.headers['Idempotency-Key'],d.requestId);assert.ok(call.url.endsWith('/'+d.requestId+'/cancel'));assert.equal(JSON.parse(call.init.body).favorite,true);
 const notRecorded={state:'notRecorded',ownerId:actor,revision:0,requestId:d.requestId,operation:null};assert.equal(favoriteOutcome(notRecorded,d).state,'notRecorded');await assert.rejects(cancelCatalogFavorite(api(async()=>response(notRecorded)),customer,d),e=>e.uncertain);
 await assert.rejects(catalogFavoriteStatus(api(async()=>response(outcome,8)),customer,d),e=>e.uncertain);
});
test('old public intentions remain valid for recovery while new intents require canonical catalogue',()=>{const d={...prepareFavorite(actor,aggregate(),'pdu',true),catalogVersion:'rc9-base-previous',catalogSha256:'0'.repeat(64)};assert.equal(validFavoriteDraft(d),true);assert.equal(validFavoriteDraft({...d,csrf:'secret'}),false);assert.equal(validFavoriteDraft({...d,revision:-1}),false)});
test('journal retains original actor/request and refuses replacement/removal by another intention',async()=>{
 const records=new Map();let created=false;
 globalThis.indexedDB={open(){const r={};queueMicrotask(()=>{r.result={createObjectStore(){created=true},close(){},transaction(){const tx={aborted:false,abort(){this.aborted=true;queueMicrotask(()=>this.onabort?.())},objectStore(){return{get(key){const read={};queueMicrotask(()=>{read.result=records.get(key);read.onsuccess?.();queueMicrotask(()=>{if(!tx.aborted)tx.oncomplete?.()})});return read},put(d){records.set(d.actorId,structuredClone(d))},delete(key){records.delete(key)}}}};return tx}};if(!created)r.onupgradeneeded?.();r.onsuccess?.()});return r}};
 try{const d=prepareFavorite(actor,aggregate(),'pdu',true);await favoriteJournal('write',actor,d);assert.deepEqual(await favoriteJournal('read',actor),d);assert.equal(await favoriteJournal('read',other),null);await assert.rejects(favoriteJournal('write',actor,{...d,requestId:id(9)}));await assert.rejects(favoriteJournal('remove',actor,{...d,favorite:false}));assert.deepEqual(await favoriteJournal('read',actor),d);await favoriteJournal('remove',actor,d);assert.equal(await favoriteJournal('read',actor),null)}finally{delete globalThis.indexedDB}
});
test('all UI labels are localised; shared browser is used by creator and consultation, with no personal path in inventory journal',async()=>{
 for(const lang of ['de','es'])assert.deepEqual(Object.keys(favoriteWords[lang]).sort(),Object.keys(favoriteWords.en).sort());
 for(const name of ['InventoryCatalogFields.jsx','InventoryCatalogDialog.jsx'])assert.match(await readFile(new URL('../src/'+name,import.meta.url),'utf8'),/<InventoryCatalogBrowser/);
 const journal=await readFile(new URL('../src/catalog-favorites-journal.ts',import.meta.url),'utf8');assert.doesNotMatch(journal,/localStorage|password|csrf|project\.ports/);
});
test('hook context A to B to A resets busy and rejects a late response from the previous A generation',async()=>{
 const source=await readFile(new URL('../src/InventoryCatalogFavorites.jsx',import.meta.url),'utf8');
 const hookSource=source.slice(source.indexOf('export function useCatalogFavorites('),source.indexOf('\nexport function InventoryCatalogFavorites(')).replace('export function','function');
 const slots=[],effects=[],reads=[];let cursor=0;
 const useState=initial=>{const index=cursor++;if(!(index in slots))slots[index]=initial;return[slots[index],value=>{slots[index]=typeof value==='function'?value(slots[index]):value}]};
 const useRef=initial=>{const index=cursor++;return slots[index]??=( {current:initial} )};
 const useEffect=(callback,deps)=>{const index=cursor++,old=slots[index];if(!old||deps.some((v,i)=>v!==old.deps[i]))effects.push(()=>{old?.cleanup?.();slots[index]={deps,cleanup:callback()}})};
 const readCatalogFavorites=(_api,context)=>new Promise(resolve=>reads.push({context,resolve}));
 const hook=new Function('useState','useEffect','useRef','readCatalogFavorites','favoriteJournal','ApiError',hookSource+';return useCatalogFavorites')(useState,useEffect,useRef,readCatalogFavorites,async()=>null,Error);
 const a={actorId:actor},props={api:a,actorId:actor,customerId:customer,userName:'synthetic',lang:'es'};
 const render=p=>{cursor=0;const result=hook(p);while(effects.length)effects.shift()();return result};
 const flush=async()=>{for(let i=0;i<12;i++)await Promise.resolve()};
 render(props);await flush();reads[0].resolve(aggregate());await flush();let state=render(props);assert.equal(state.ready,true);
 const oldReload=state.reload();await flush();state=render(props);assert.equal(state.busy,true);
 const b={...props,customerId:other};render(b);await flush();reads[2].resolve({...aggregate(2,['ups']),customerId:other});await flush();assert.equal(render(b).busy,false);
 render(props);await flush();reads[3].resolve(aggregate(9,['ups']));await flush();state=render(props);assert.equal(state.ready,true);assert.equal(state.data.revision,9);
 reads[1].resolve(aggregate(1,['pdu']));await oldReload;await flush();state=render(props);assert.equal(state.busy,false);assert.equal(state.data.revision,9);assert.deepEqual(state.data.presetKeys,['ups']);
});
