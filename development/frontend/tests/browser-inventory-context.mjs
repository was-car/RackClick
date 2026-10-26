import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
import path from 'node:path';
import {runScenario,infrastructure,snapshot,saved,submit,normalize,fixture as ids,poll} from './browser-quince-support.mjs';
const journal=tab=>tab.evaluate(`new Promise((resolve,reject)=>{const r=indexedDB.open('RackClick.PendingOperations.v1',1);r.onerror=()=>reject(Error('journal'));r.onsuccess=()=>{const db=r.result,q=db.transaction('pending').objectStore('pending').getAll();q.onsuccess=()=>{db.close();resolve(q.result)}}})`);
const state=p=>{const value=normalize(p);value.revision=0;return value};
await runScenario(async({first,checks,shot,out,origin,password})=>{
 await infrastructure(first);const original=await snapshot(first),actor=await first.evaluate(`fetch('/api/v1/me').then(r=>r.json()).then(m=>m.user.id)`);
 async function grow(){
  if(!await first.evaluate(`!!document.querySelector('[data-edit-groups="${ids.a}"]')`)){await first.click(`[data-rack-id="${ids.rackA}"] .rc-rack-open`);await first.wait(`!!document.querySelector('[data-edit-groups="${ids.a}"]')`,'rack editor');}
  await first.click(`[data-edit-groups="${ids.a}"]`);await first.wait(`!!document.querySelector('dialog .rc-port-groups')`,'groups editor');await first.field('dialog .rc-port-groups > div:first-of-type input[type=number]','1');await submit(first);await saved(first);
  await first.wait(`!!document.querySelector('[data-undo-groups]')&&!document.querySelector('[data-undo-groups]').disabled`,'undo candidate');await first.click('[data-undo-groups]');await first.wait(`!!document.querySelector('[data-confirm-group-undo]')`,'undo scope');await first.click('[data-confirm-group-undo]');
 }
 async function switchActor(name){
  // Deliberate same-profile account replacement, equivalent to another tab signing in.
  const status=await first.evaluate(`fetch('/api/v1/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:${JSON.stringify(name)},password:${JSON.stringify(password)}})}).then(r=>r.status)`);assert.equal(status,200);
  // Controlled event invokes the real application reload while its modal is open.
  await first.evaluate(`[...document.querySelectorAll('.rc-customer-header button')].find(b=>b.textContent==='Actualizar').click()`);
  await first.wait(`document.querySelector('.ir-nav')?.textContent.includes(${JSON.stringify(name)})&&!document.querySelector('dialog[open]')`,'new actor replaces inventory and dialog');
  await first.wait(`document.querySelector('.rc-inventory-toolbar [role=status]')?.textContent==='Cargado desde el servidor'`,'new actor inventory loaded');
 }
 async function late(stage,suffix,action){await first.send('Fetch.enable',{patterns:[{urlPattern:origin+'/api/v1/customers/'+ids.customer+suffix,requestStage:stage}]});await action();return poll(()=>first.paused?.shift(),'held HTTP '+stage);}
 async function release(paused){await first.send('Fetch.continueRequest',{requestId:paused.requestId});await first.send('Fetch.disable');await first.evaluate(`new Promise(r=>setTimeout(r,150))`);}
 async function recover(){await first.wait(`[...document.querySelectorAll('button')].some(b=>b.textContent==='Recuperar operación pendiente')`,'original actor pending intent');await first.button('Recuperar operación pendiente');await first.wait(`!!document.querySelector('[data-query-pending]')`,'original recovery dialog');await first.click('[data-query-pending]');}

 await grow();let held=await late('Response','/commands',()=>submit(first));assert.equal(held.responseStatusCode,200);const committed=await snapshot(first),pending=(await journal(first))[0];assert.equal(pending.actorId,actor);assert.deepEqual(state(committed),state(original));
 await switchActor('move-second');await release(held);
 assert.deepEqual((await journal(first))[0],pending,'unmounted old submit keeps its original uncertain journal');
 assert.equal(await first.evaluate(`document.body.textContent.includes('Recuperar operación pendiente')`),false,'other actor never sees the previous actor intent');
 assert.equal(await first.evaluate(`document.querySelector('.rc-inventory-toolbar [role=status]').textContent`),'Cargado desde el servidor','old callback cannot mark the new view saved');
 assert.deepEqual(normalize(await snapshot(first)),normalize(committed));await shot(first,'actor-after-late-submit.png');
 await switchActor('move-admin');await recover();await saved(first);assert.equal((await journal(first)).length,0);
 checks.push('Actual account switch during held committed undo response unmounts the original panel; old callback neither clears its journal nor marks the next actor saved. Original actor recovers the exact committed receipt.');

 await grow();held=await late('Request','/commands',()=>submit(first));await first.send('Fetch.failRequest',{requestId:held.requestId,errorReason:'Failed'});await first.send('Fetch.disable');
 await first.wait(`!!document.querySelector('dialog [role=alert]')&&!document.querySelector('dialog button:disabled')`,'unsent inverse pending');
 const cancelPending=(await journal(first))[0],grown=await snapshot(first);
 held=await late('Response','/operations/'+cancelPending.operation.requestId+'/cancel',()=>first.button('Cancelar operación pendiente'));assert.equal(held.responseStatusCode,200);
 await switchActor('move-second');await release(held);assert.deepEqual((await journal(first))[0],cancelPending);assert.equal(await first.evaluate(`document.body.textContent.includes('Recuperar operación pendiente')`),false);assert.deepEqual(normalize(await snapshot(first)),normalize(grown));
 await switchActor('move-admin');await recover();await first.wait(`document.querySelector('[data-operation-query-status]')?.dataset.operationQueryStatus==='cancelled'`,'recover terminal cancellation after account switch');assert.equal((await journal(first)).length,0);await shot(first,'original-actor-cancellation.png');await first.button('Cerrar');
 checks.push('Held cancellation response also leaves the original journal when the actor changes; the original actor later queries cancelled, never reapplies the inverse, and clears only that intent.');

 await first.click(`[data-rack-id="${ids.rackA}"] .rc-rack-open`);await first.wait(`!!document.querySelector('[data-edit-groups="${ids.a}"]')`,'cleanup rack');
 const added=grown.ports.filter(p=>!original.ports.some(o=>o.id===p.id));assert.equal(added.length,1);
 await first.click(`[data-edit-groups="${ids.a}"]`);await first.wait(`!!document.querySelector('dialog .rc-port-groups')`,'cleanup groups');
 const position=grown.ports.filter(p=>p.groupId===ids.ga).findIndex(p=>p.id===added[0].id);await first.evaluate(`document.querySelectorAll('dialog .rc-port-groups > div:first-of-type .rc-port-selection input')[${position}].click()`);await submit(first);await first.wait(`[...document.querySelectorAll('dialog button')].some(b=>b.textContent==='Confirmar eliminación')`,'preview');await submit(first);await saved(first);
 const final=await snapshot(first);assert.deepEqual(state(final),state(original));assert.equal((await journal(first)).length,0);checks.push('Normal previewed edit restores the synthetic added port; final inventory equals the original without replaying either operation.');
 await writeFile(path.join(out,'expected-project.json'),JSON.stringify(final,null,2)+'\n');
});
