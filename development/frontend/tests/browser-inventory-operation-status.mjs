import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
import path from 'node:path';
import {runScenario,infrastructure,snapshot,saved,submit,normalize,fixture as ids,poll} from './browser-quince-support.mjs';
const journal=tab=>tab.evaluate(`new Promise((resolve,reject)=>{const r=indexedDB.open('RackClick.PendingOperations.v1',1);r.onerror=()=>reject(Error('journal'));r.onsuccess=()=>{const db=r.result,q=db.transaction('pending').objectStore('pending').getAll();q.onsuccess=()=>{db.close();resolve(q.result)}}})`);
const state=value=>{const p=normalize(value);p.revision=0;return p};
await runScenario(async({first,session,checks,shot,out,origin})=>{
 await infrastructure(first);const original=await snapshot(first);
 const observed=[];first.ws.addEventListener('message',event=>{const message=JSON.parse(event.data);if(message.method==='Network.requestWillBeSent'){const r=message.params.request;observed.push({path:new URL(r.url).pathname,method:r.method,requestId:Object.entries(r.headers).find(([key])=>key.toLowerCase()==='idempotency-key')?.[1]||null})}});
 await first.click(`[data-rack-id="${ids.rackA}"] .rc-rack-open`);await first.wait(`!!document.querySelector('[data-edit-groups="${ids.a}"]')`,'group editor ready');
 const requests=async()=>observed.slice();
 async function grow(){await first.click(`[data-edit-groups="${ids.a}"]`);await first.wait(`!!document.querySelector('dialog .rc-port-groups')`,'groups form');await first.field('dialog .rc-port-groups > div:first-of-type input[type=number]','1');await submit(first);await saved(first);await first.wait(`!!document.querySelector('[data-undo-groups]')&&!document.querySelector('[data-undo-groups]').disabled`,'structural candidate');}
 async function uncertain(stage){
  await first.click('[data-undo-groups]');await first.wait(`!!document.querySelector('[data-confirm-group-undo]')`,'scope');await first.click('[data-confirm-group-undo]');
  await first.send('Fetch.enable',{patterns:[{urlPattern:origin+'/api/v1/customers/'+ids.customer+'/commands',requestStage:stage}]});await submit(first);
  const paused=await poll(()=>first.paused?.shift(),'intercepted inverse');if(stage==='Response')assert.equal(paused.responseStatusCode,200);
  await first.send('Fetch.failRequest',{requestId:paused.requestId,errorReason:'Failed'});await first.send('Fetch.disable');
  await first.wait(`!!document.querySelector('dialog [role=alert]')&&!document.querySelector('[data-query-pending]').disabled`,'uncertain inverse');
  const record=(await journal(first))[0];assert.equal(JSON.parse(record.operation.body).type,'operations.compensate');return record;
 }
 async function query(){const before=await requests();await first.click('[data-query-pending]');await first.wait(`!document.querySelector('[data-query-pending]')||!document.querySelector('[data-query-pending]').disabled`,'query finished');const delta=(await requests()).slice(before.length);assert.equal(delta.filter(r=>r.method!=='GET').length,0,'query never sends a mutation');assert.equal(delta.filter(r=>r.path.endsWith('/operations/'+pending.operation.requestId)).length,1);}
 await grow();let pending=await uncertain('Response');const committed=await snapshot(first);assert.deepEqual(state(committed),state(original));
 const other=await session('move-second');await infrastructure(other);
 const isolated=await other.evaluate(`fetch('/api/v1/customers/${ids.customer}/operations/${pending.operation.requestId}').then(r=>r.json())`);assert.equal(isolated.state,'notRecorded','receipt is scoped to authenticated actor');
 await query();await saved(first);assert.equal((await journal(first)).length,0);assert.deepEqual(normalize(await snapshot(first)),normalize(committed));
 checks.push('Lost committed structural response: GET recovers the original receipt without any mutation; another authenticated actor cannot read that receipt.');

 await grow();pending=await uncertain('Request');const unsent=await snapshot(first);await query();
 await first.wait(`document.querySelector('[data-operation-query-status]')?.dataset.operationQueryStatus==='notRecorded'`,'explicit nonterminal status');
 assert.deepEqual((await journal(first))[0],pending,'notRecorded keeps the exact original journal');assert.deepEqual(normalize(await snapshot(first)),normalize(unsent));await shot(first,'not-recorded.png');
 await submit(first);await saved(first);assert.equal((await journal(first)).length,0);assert.deepEqual(state(await snapshot(first)),state(original));
 const retries=(await requests()).filter(r=>r.path.endsWith('/commands')&&r.requestId===pending.operation.requestId);assert.equal(retries.length,2);checks.push('Predispatch loss: GET notRecorded preserves the original request and data; explicit retry uses the same key and commits once.');

 await grow();pending=await uncertain('Request');const beforeCancel=await snapshot(first);await query();
 const sameActor=await session();await infrastructure(sameActor);
 const cancelled=await sameActor.evaluate(`(async()=>{const me=await fetch('/api/v1/me').then(r=>r.json());const r=await fetch('/api/v1/customers/${ids.customer}/operations/${pending.operation.requestId}/cancel',{method:'POST',headers:{'Content-Type':'application/json','X-RackClick-CSRF':me.csrf,'X-RackClick-Actor':me.user.id,'If-Match':${JSON.stringify(pending.operation.etag)},'Idempotency-Key':${JSON.stringify(pending.operation.requestId)}},body:${JSON.stringify(pending.operation.body)}});if(!r.ok)throw Error('cancel '+r.status);return r.json()})()`);
 assert.equal(cancelled.state,'cancelled');await query();await first.wait(`document.querySelector('[data-operation-query-status]')?.dataset.operationQueryStatus==='cancelled'`,'terminal cancellation status');
 assert.equal((await journal(first)).length,0);assert.deepEqual(normalize(await snapshot(first)),normalize(beforeCancel));assert.equal(await first.evaluate(`document.querySelector('dialog button[type=submit]').disabled`),true);await shot(first,'cancelled.png');
 const late=await sameActor.evaluate(`(async()=>{const me=await fetch('/api/v1/me').then(r=>r.json());const r=await fetch('/api/v1/customers/${ids.customer}/commands',{method:'POST',headers:{'Content-Type':'application/json','X-RackClick-CSRF':me.csrf,'X-RackClick-Actor':me.user.id,'If-Match':${JSON.stringify(pending.operation.etag)},'Idempotency-Key':${JSON.stringify(pending.operation.requestId)}},body:${JSON.stringify(pending.operation.body)}});return {status:r.status,error:(await r.json()).error}})()`);
 assert.deepEqual(late,{status:409,error:'operation_cancelled'});checks.push('Cancellation from another session of the original actor: GET shows server-confirmed cancellation, clears only its journal, disables retry and leaves inventory untouched; late POST409 is fenced.');
 await first.button('Cerrar');
 // Return the synthetic added port through the normal, previewed editor.
 const added=beforeCancel.ports.filter(p=>!original.ports.some(o=>o.id===p.id));assert.equal(added.length,1);
 await first.click(`[data-edit-groups="${ids.a}"]`);await first.wait(`!!document.querySelector('dialog .rc-port-groups')`,'cleanup editor');
 const position=beforeCancel.ports.filter(p=>p.groupId===ids.ga).findIndex(p=>p.id===added[0].id);
 await first.evaluate(`document.querySelectorAll('dialog .rc-port-groups > div:first-of-type .rc-port-selection input')[${position}].click()`);await submit(first);await first.wait(`[...document.querySelectorAll('dialog button')].some(b=>b.textContent==='Confirmar eliminación')`,'server preview');await submit(first);await saved(first);
 const final=await snapshot(first);assert.deepEqual(state(final),state(original));
 const reader=await session('move-reader');await infrastructure(reader);const denied=await reader.evaluate(`fetch('/api/v1/customers/${ids.other}/operations/${pending.operation.requestId}').then(r=>r.status)`);assert.equal(denied,404);checks.push('Real server denies status outside the reader customer scope; final normal edit restores the original inventory.');
 await writeFile(path.join(out,'expected-project.json'),JSON.stringify(final,null,2)+'\n');
});
