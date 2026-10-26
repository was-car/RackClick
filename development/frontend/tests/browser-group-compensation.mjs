import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
import path from 'node:path';
import {runScenario,infrastructure,snapshot,saved,submit,normalize,fixture as ids,poll} from './browser-quince-support.mjs';

const journal=tab=>tab.evaluate(`new Promise((resolve,reject)=>{const r=indexedDB.open('RackClick.PendingOperations.v1',1);r.onerror=()=>reject(Error('journal'));r.onsuccess=()=>{const db=r.result,q=db.transaction('pending').objectStore('pending').getAll();q.onsuccess=()=>{db.close();resolve(q.result)}}})`);
const state=project=>{const p=normalize(project);p.revision=0;return p};
await runScenario(async({first,session,checks,shot,out,origin})=>{
 await infrastructure(first);const original=await snapshot(first);
 await first.click(`[data-rack-id="${ids.rackA}"] .rc-rack-open`);
 await first.wait(`!!document.querySelector('[data-vport="${ids.pa}"]')`,'rack ready');
 async function edit(){
  await first.click(`[data-edit-groups="${ids.a}"]`);
  await first.wait(`!!document.querySelector('dialog .rc-port-groups')`,'groups form');
 }
 async function scope(kind,ports,groups,connections){
  await first.wait(`!!document.querySelector('[data-undo-groups]')&&!document.querySelector('[data-undo-groups]').disabled`,'structural candidate');
  await first.click('[data-undo-groups]');await first.wait(`!!document.querySelector('[data-group-compensation="${kind}"]')`,'exact structural scope');
  for(const [type,expected] of [['port',ports],['group',groups],['connection',connections]])assert.deepEqual(await first.evaluate(`[...document.querySelectorAll('[data-undo-${type}]')].map(el=>el.dataset.undo${type[0].toUpperCase()+type.slice(1)}).sort()`),[...expected].sort());
  const before=await snapshot(first);await submit(first);assert.deepEqual(state(await snapshot(first)),state(before),'unchecked confirmation cannot write');
  assert.equal(await first.evaluate(`document.querySelector('[data-confirm-group-undo]').checked`),false);
  await first.click('[data-confirm-group-undo]');
 }
 await edit();await first.field('dialog .rc-port-groups > div:first-of-type input[type=number]','1');await submit(first);await saved(first);
 const grown=await snapshot(first),added=grown.ports.filter(p=>!original.ports.some(old=>old.id===p.id));assert.equal(added.length,1);
 await scope('groupGrowth',added.map(p=>p.id),[],[]);await shot(first,'growth-scope.png');
 await first.button('Cancelar');await scope('groupGrowth',added.map(p=>p.id),[],[]);await submit(first);await saved(first);
 assert.deepEqual(state(await snapshot(first)),state(original));checks.push('Growth: exact IDs, checkbox required, cancel/reopen, confirmed undo and all original rows preserved.');
 await edit();await first.evaluate(`document.querySelectorAll('dialog .rc-port-groups > div')[1].querySelector('button').click()`);await submit(first);
 await first.wait(`[...document.querySelectorAll('dialog button')].some(b=>b.textContent==='Confirmar eliminación')`,'server deletion preview');await submit(first);await saved(first);
 await scope('groupReduction',[ids.undoPort],[ids.undoGroup],[ids.undoCable]);await shot(first,'reduction-scope.png');
 await first.send('Fetch.enable',{patterns:[{urlPattern:origin+'/api/v1/customers/'+ids.customer+'/commands',requestStage:'Response'}]});await submit(first);
 const paused=await poll(()=>first.paused?.shift(),'committed undo response');assert.equal(paused.responseStatusCode,200);await first.send('Fetch.failRequest',{requestId:paused.requestId,errorReason:'Failed'});await first.send('Fetch.disable');
 await first.wait(`!!document.querySelector('dialog [role=alert]')&&!document.querySelector('dialog button:disabled')`,'uncertain operation retained');
 const pending=(await journal(first))[0];assert.deepEqual(Object.keys(JSON.parse(pending.operation.body).payload),['operationId']);assert.equal(pending.label,'undoGroups');
 await first.send('Page.reload');await first.wait(`!!document.querySelector('[data-customer-id="${ids.customer}"]')`,'session after reload');await first.click(`[data-customer-id="${ids.customer}"]`);
 await first.wait(`[...document.querySelectorAll('button')].some(b=>b.textContent.trim()==='Recuperar operación pendiente')`,'durable pending undo');
 assert.deepEqual((await journal(first))[0].operation,pending.operation);await first.button('Recuperar operación pendiente');await first.wait(`!!document.querySelector('dialog[open]')`,'recovery dialog');await submit(first);await saved(first);
 assert.equal((await journal(first)).length,0);const final=await snapshot(first);assert.deepEqual(state(final),state(original));assert.equal(final.revision,original.revision+4);
 checks.push('Reduction: removed group/port/cable UUIDs, server preview, lost committed response, reload and exact original replay; no duplicate commit.');
 const second=await session('move-second');await infrastructure(second);assert.deepEqual(normalize(await snapshot(second)),normalize(final));checks.push('Independent browser context reads the same restored data.');
 const reader=await session('move-reader');await infrastructure(reader);assert.equal(await reader.evaluate(`!!document.querySelector('[data-undo-groups]')||!!document.querySelector('[data-undo-ports]')`),false);checks.push('Reader has no undo candidate or editing privilege.');
 assert.equal(await first.evaluate(`!!document.querySelector('img[src=x]')`),false);await shot(first,'restored-inventory.png');
 await writeFile(path.join(out,'expected-project.json'),JSON.stringify(final,null,2)+'\n');
});
